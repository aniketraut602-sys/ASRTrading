import abc
import asyncio
from typing import Optional, Dict
from asr_trading.strategy.planner import TradePlan
from asr_trading.core.logger import logger
from asr_trading.core.avionics import CircuitBreaker
from asr_trading.core.avionics import CircuitBreaker
# telegram_bot imported locally to avoid circular dependency
from asr_trading.core.auditor import Auditor
from asr_trading.core.config import cfg

class BrokerAdapter(abc.ABC):
    @abc.abstractmethod
    def get_name(self) -> str: pass
    
    @abc.abstractmethod
    async def place_order(self, plan: TradePlan) -> Dict: pass

class KiteAdapter(BrokerAdapter):
    def get_name(self): return "KITE_ZERODHA"
    async def place_order(self, plan: TradePlan):
        # Implementation Stub using KiteConnect
        # kite.place_order(variety=kite.VARIETY_REGULAR, ...)
        logger.info(f"KiteAdapter: Placing order for {plan.symbol} Qty={plan.quantity}")
        return {"order_id": "KITE_1001", "status": "SUBMITTED"}

class AlpacaAdapter(BrokerAdapter):
    def get_name(self): return "ALPACA_US"
    async def place_order(self, plan: TradePlan):
        logger.info(f"AlpacaAdapter: Placing order for {plan.symbol} Qty={plan.quantity}")
        return {"order_id": "ALP_999", "status": "SUBMITTED"}

class ExecutionManager:
    """
    Executes TradePlans using Dual-Path routing.
    """
    def __init__(self):
        self.primary: Optional[BrokerAdapter] = None
        self.secondary: Optional[BrokerAdapter] = None
        self.used_plan_ids = set() # Idempotency check
        self.pending_plans = {}    # Semi-Auto Holding Area
        self.lock = asyncio.Lock()

    def set_brokers(self, primary: BrokerAdapter, secondary: BrokerAdapter):
        self.primary = primary
        self.secondary = secondary

    async def _notify_success(self, plan: TradePlan):
        """Helper to format and send trade alert"""
        # Avoid Circular Import
        try:
             from asr_trading.web.telegram_bot import telegram_bot
             if telegram_bot.running:
                 trade_data = {
                     "ticker": plan.symbol,
                     "strategy": plan.plan_code, # e.g. "A" (The Plan Code)
                     "strategy_id": getattr(plan, 'strategy_id', 'Unknown'), # Pass original strategy name if available
                     "confidence": plan.confidence, 
                     "action": plan.side,
                     "quantity": plan.quantity,
                     "price": plan.entry_price or plan.limit_price,
                     "mode": "PAPER" if cfg.IS_PAPER else "LIVE"
                 }
                 await telegram_bot.notify_trade(trade_data)
        except ImportError:
             pass

    # @CircuitBreaker(name="execution_manager_place")
    async def execute_plan(self, plan: TradePlan, force_paper: bool = False) -> Dict:
        """
        Routes the order.
        """
        import traceback
        try:
            # 17.2 Zero-Discrepancy Check (Double check before wire)
            Auditor.audit_plan_integrity(plan)

            # 1. Idempotency Check (Check only)
            async with self.lock:
                if plan.plan_id in self.used_plan_ids:
                    logger.warning(f"Execution: Duplicate Plan ID {plan.plan_id}. Ignoring.")
                    return {"status": "SKIPPED", "reason": "Duplicate Plan ID", "order_id": getattr(plan, 'order_id', None)}
            
            # 1.5 Semi-Auto Intercept
            # NOTE: If force_paper is True, we might still want Semi-Auto simulation?
            # User requirement: "go through same frame work". So YES.
            if cfg.EXECUTION_TYPE == "SEMI":
                # Store and Notify
                self.pending_plans[plan.plan_id] = plan
                logger.info(f"ExecutionManager: Plan {plan.plan_id} HELD for Approval (SEMI Mode)")
                
                # Request Approval
                # Avoid Circular Import
                from asr_trading.web.telegram_bot import telegram_bot
                await telegram_bot.request_approval({
                    "plan_id": plan.plan_id,
                    "strategy": plan.plan_code,
                    "action": plan.side,
                    "ticker": plan.symbol,
                    "size": plan.quantity,
                    "price": plan.entry_price or plan.limit_price,
                    "confidence": plan.confidence,
                    "stop_loss": plan.stop_loss,
                    "mode": "PAPER" if cfg.IS_PAPER else "LIVE"
                })
                return {"status": "PENDING_APPROVAL"}

            # Mark as used (Auto Mode)
            async with self.lock:
                self.used_plan_ids.add(plan.plan_id)

            return await self._send_to_brokers(plan, force_paper)

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Execution Error: {e}")
            raise e

    async def confirm_execution(self, plan_id: str) -> Dict:
        """
        Called by Telegram Bot to release a pending plan.
        """
        if plan_id not in self.pending_plans:
            return {"status": "PLAN_NOT_FOUND_OR_EXPIRED"}
        
        plan = self.pending_plans.pop(plan_id)
        
        # Mark as used before execution
        async with self.lock:
             self.used_plan_ids.add(plan.plan_id)
             
        logger.info(f"ExecutionManager: Plan {plan_id} APPROVED by User. Executing.")
        
        # Call Internal Execute Logic
        is_manual_paper = (plan.plan_code == "MANUAL_PAPER")
        return await self._send_to_brokers(plan, force_paper=is_manual_paper)

    async def _send_to_brokers(self, plan: TradePlan, force_paper: bool = False) -> Dict:
        # Override for Paper Mode
        active_primary = self.primary
        if force_paper:
             from asr_trading.execution.paper_adapter import PaperAdapter
             active_primary = PaperAdapter()
        
        # 2. Primary Path
        if active_primary:
            try:
                res = await active_primary.place_order(plan)
                logger.info(f"Execution: Primary ({active_primary.get_name()}) successful: {res}")
                
                # Success Hook
                await self._notify_success(plan)

                # 18.x Connect to Lifecycle Manager (OrderManager)
                from asr_trading.execution.order_manager import order_engine
                order_engine.register_execution(plan, res.get("order_id", "UNKNOWN"))
                
                return res
            except Exception as e:
                logger.error(f"Execution: Primary ({self.primary.get_name()}) FAILED: {e}. Trying Secondary.")
        
        # 3. Secondary Path (Hot Standby)
        if self.secondary:
            try:
                res = await self.secondary.place_order(plan)
                logger.info(f"Execution: Secondary ({self.secondary.get_name()}) successful: {res}")
                
                # Success Hook
                await self._notify_success(plan)
                
                # 18.x Connect to Lifecycle Manager (OrderManager)
                # This ensures Plan A monitoring starts immediately
                from asr_trading.execution.order_manager import order_engine
                order_engine.register_execution(plan, res.get("order_id", "UNKNOWN"))
                
                # Plan I (Shadow Order) enacted
                return res
            except Exception as e:
                logger.critical(f"Execution: Secondary ({self.secondary.get_name()}) FAILED: {e}. ORDER FAILED.")
                return {"status": "FAILED_ALL_PATHS"}

        return {"status": "NO_BROKERS_CONFIGURED"}

    def record_trade_result(self, plan_id: str, strategy_id: str, symbol: str, pnl: float, outcome: int, features: Optional[Dict] = None):
        """
        Phase 18: Callback for Trade Completion.
        Updates Journal and Governance.
        """
        from asr_trading.core.journal import journal
        from asr_trading.brain.governance import governance
        
        # 1. Log to Journal (System of Record)
        journal.log_trade({
            "strategy_id": strategy_id,
            "symbol": symbol,
            "pnl": pnl,
            "outcome": outcome, # 1=Win, 0=Loss
            "side": "UNKNOWN", # Could be passed in if needed
            "timestamp": asyncio.get_event_loop().time(),
            "features": features # 18.6 Feature Snapshot
        })
        
        # 2. Update Governance (Survivability)
        governance.update_trade(strategy_id, success=(outcome == 1))
        logger.info(f"Execution: Recorded trade outcome for {strategy_id}: {'WIN' if outcome==1 else 'LOSS'}")

    async def check_order_status(self, order_id: str) -> Dict:
        """
        Queries the primary broker for order status.
        """
        if self.primary and hasattr(self.primary, "get_order_status"):
             return await self.primary.get_order_status(order_id)
        
        # Fallback if adapter doesn't support generic check or is paper
        if cfg.IS_PAPER:
            # Paper mode usually assumes FILLED immediately, but for robustness:
            return {"status": "FILLED", "raw": "PAPER_AUTO_FILL"}
            
        return {"status": "UNKNOWN", "reason": "Adapter does not support status check"}

execution_manager = ExecutionManager()

if cfg.IS_PAPER:
    from asr_trading.execution.paper_adapter import PaperAdapter
    logger.info("ExecutionManager: Initializing in PAPER mode")
    execution_manager.set_brokers(PaperAdapter(), None)
else:
    logger.info("ExecutionManager: Initializing in LIVE/MOCK mode")
    execution_manager.set_brokers(KiteAdapter(), AlpacaAdapter())
