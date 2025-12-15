import abc
import asyncio
from typing import Optional, Dict
from asr_trading.strategy.planner import TradePlan
from asr_trading.core.logger import logger
from asr_trading.core.avionics import CircuitBreaker
from asr_trading.core.avionics import CircuitBreaker
from asr_trading.web.telegram_bot import telegram_bot
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
        if telegram_bot.running:
            trade_data = {
                "ticker": plan.symbol,
                "strategy": "Plan " + plan.plan_code, # e.g. "Plan A"
                "confidence": plan.confidence, # 17.1 Audit Fix: Real data
                "action": plan.side
            }
            await telegram_bot.notify_trade(trade_data)

    @CircuitBreaker(name="execution_manager_place")
    async def execute_plan(self, plan: TradePlan) -> Dict:
        """
        Routes the order.
        """
        """
        Routes the order.
        """
        # 17.2 Zero-Discrepancy Check (Double check before wire)
        Auditor.audit_plan_integrity(plan)

        # 1. Idempotency Check (Thread/Async Safe)
        async with self.lock:
            if plan.plan_id in self.used_plan_ids:
                logger.warning(f"Execution: Duplicate Plan ID {plan.plan_id}. Ignoring.")
                return {"status": "IGNORED_DUPLICATE"}
        
        # 1.5 Semi-Auto Intercept
        if cfg.EXECUTION_TYPE == "SEMI":
            # Store and Notify
            self.pending_plans[plan.plan_id] = plan
            logger.info(f"ExecutionManager: Plan {plan.plan_id} HELD for Approval (SEMI Mode)")
            
            # Request Approval
            await telegram_bot.request_approval({
                "plan_id": plan.plan_id,
                "strategy": plan.plan_code,
                "action": plan.side,
                "ticker": plan.symbol,
                "size": plan.quantity,
                "confidence": plan.confidence
            })
            return {"status": "PENDING_APPROVAL"}

        # Mark as used (Auto Mode)
        async with self.lock:
            self.used_plan_ids.add(plan.plan_id)

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
        
        # Call Internal Execute Logic directly to bypass the check (needs refactor or duplicate logic)
        # To reuse logic, we temporarily switch mode or call a private method.
        # Cleaner: Extract actual broker call to _send_to_brokers
        return await self._send_to_brokers(plan)

    async def _send_to_brokers(self, plan: TradePlan) -> Dict:
        # 2. Primary Path
        if self.primary:
            try:
                res = await self.primary.place_order(plan)
                logger.info(f"Execution: Primary ({self.primary.get_name()}) successful: {res}")
                
                # Success Hook
                await self._notify_success(plan)
                
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
                
                # Plan I (Shadow Order) enacted
                return res
            except Exception as e:
                logger.critical(f"Execution: Secondary ({self.secondary.get_name()}) FAILED: {e}. ORDER FAILED.")
                return {"status": "FAILED_ALL_PATHS"}

        return {"status": "NO_BROKERS_CONFIGURED"}

    def record_trade_result(self, plan_id: str, strategy_id: str, symbol: str, pnl: float, outcome: int):
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
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # 2. Update Governance (Survivability)
        governance.update_trade(strategy_id, success=(outcome == 1))
        logger.info(f"Execution: Recorded trade outcome for {strategy_id}: {'WIN' if outcome==1 else 'LOSS'}")

execution_manager = ExecutionManager()

if cfg.IS_PAPER:
    from asr_trading.execution.paper_adapter import PaperAdapter
    logger.info("ExecutionManager: Initializing in PAPER mode")
    execution_manager.set_brokers(PaperAdapter(), None)
else:
    logger.info("ExecutionManager: Initializing in LIVE/MOCK mode")
    execution_manager.set_brokers(KiteAdapter(), AlpacaAdapter())
