from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
from asr_trading.strategy.base import TradeSignal
import uuid
from datetime import datetime

class OrderManager:
    def __init__(self):
        self.positions = {} # symbol -> {entry, size, sl, tp, status, strategy}
        self.orders = []
        self.is_paper = cfg.IS_PAPER_TRADING

    def execute_signal(self, signal: TradeSignal, size: float = 1.0):
        if signal.action == "HOLD":
            return

        logger.info(f"Executing {signal.action} on {signal.symbol} (Confidence: {signal.confidence}%)")
        
        if self.is_paper:
            self._execute_paper(signal, size)
        else:
            logger.warning("Real execution not implemented yet. Falling back to paper.")
            self._execute_paper(signal, size)

    def register_execution(self, plan: 'TradePlan', order_id: str):
        """
        Manually register a trade (e.g. from ExecutionManager) for monitoring.
        This activates Plan A (Lifecycle Management).
        """
        logger.info(f"OrderManager: Registering MANNUAL/AUTO trade for monitoring: {plan.symbol}")
        
        # 1. Deduce SL/TP if not in plan (Plan A Defaults)
        sl = plan.stop_loss
        tp = plan.take_profit
        
        if sl == 0.0:
            # Auto-Calculate Safety Nets if missing (Safety Plan)
            # Default: 1% SL, 2% TP (Scalping)
            entry = plan.entry_price if plan.entry_price > 0 else 0.0
            # If entry is 0 (Market Order), we might need to fetch current price or wait for fill update.
            # ideally Plan should have estimated entry.
            if entry > 0:
                if plan.side == "BUY":
                    sl = entry * 0.99
                    tp = entry * 1.02
                else:
                     sl = entry * 1.01
                     tp = entry * 0.98
        
        self.positions[plan.symbol] = {
            "entry": plan.entry_price,
            "current_price": plan.entry_price, # Will update
            "size": plan.quantity,
            "sl": sl,
            "tp": tp,
            "strategy": plan.plan_code,
            "status": "SUBMITTED", # Default to Submitted (Pending at Broker)
            "plan": "A",
            "order_id": order_id,
            "features": getattr(plan, 'features', None) # 18.6 Persist features
        }
        logger.info(f"OrderManager: Monitoring ACTIVE for {plan.symbol}. SL={sl:.2f}, TP={tp:.2f}")

    def _execute_paper(self, signal: TradeSignal, size: float):
        order_id = str(uuid.uuid4())[:8]
        order = {
            "id": order_id,
            "symbol": signal.symbol,
            "action": signal.action,
            "price": signal.entry_price,
            "size": size,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "time": datetime.utcnow(),
            "status": "FILLED"
        }
        self.orders.append(order)
        
        if signal.action == "BUY":
            self.positions[signal.symbol] = {
                "entry": signal.entry_price,
                "current_price": signal.entry_price,
                "size": size,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "strategy": signal.strategy_name,
                "status": "FILLED", # Paper is instant fill
                "plan": "A",
                "order_id": order_id
                # Note: Signals from legacy strategy (execute_signal) might lack features
            }
        elif signal.action == "SELL" and signal.symbol in self.positions:
            # Assume closing
            # Use close_position to handle PnL
            self.close_position(signal.symbol, "Legacy Signal Sell")
            
        logger.info(f"Paper Order {order_id} FILLED: {signal.action} {signal.symbol} @ {signal.entry_price}")

    async def monitor_lifecycle(self):
        """
        Async loop to sync order status from Broker.
        """
        from asr_trading.execution.execution_manager import execution_manager
        
        for sym, pos in list(self.positions.items()):
            # Only check status if not yet FILLED (i.e. SUBMITTED or OPEN)
            if pos['status'] in ["SUBMITTED", "OPEN", "PARTIALLY_FILLED"]:
                order_id = pos.get('order_id')
                if not order_id: continue
                
                try:
                    res = await execution_manager.check_order_status(order_id)
                    new_status = res.get("status", "UNKNOWN")
                    
                    if new_status == "FILLED":
                         pos['status'] = "FILLED"
                         # Update precise entry price if available
                         if res.get('avg_price', 0) > 0:
                             pos['entry'] = res['avg_price']
                             pos['size'] = res.get('filled_qty', pos['size'])
                         logger.info(f"OrderManager: {sym} Order {order_id} CONFIRMED FILLED. entry={pos['entry']} size={pos['size']}")
                    
                    elif new_status == "CANCELLED" or new_status == "REJECTED":
                        logger.warning(f"OrderManager: {sym} Order {order_id} failed with status {new_status}. Removing.")
                        del self.positions[sym]
                        continue

                    # Update intermediate states (SUBMITTED -> OPEN)
                    elif new_status in ["SUBMITTED", "OPEN", "PARTIALLY_FILLED"]:
                         if pos['status'] != new_status:
                             logger.info(f"OrderManager: {sym} Order {order_id} state change: {pos['status']} -> {new_status}")
                             pos['status'] = new_status
                        
                except Exception as e:
                    logger.error(f"OrderManager: Status check failed for {sym}: {e}")

    async def update_positions(self, market_data: dict):
        """
        Unified Execution Monitor Loop.
        Checks Plan A constraints and triggers State Transitions if needed.
        Now Async.
        """
        # 1. Sync Lifecycle (Broker State)
        await self.monitor_lifecycle()

        # 2. Monitor PnL (Internal State)
        for sym, pos in list(self.positions.items()):
            # Only monitor active positions
            if pos['status'] != "FILLED" and not self.is_paper:
                 # In Paper, we might assume filled, but explicit check is better.
                 # If status is still SUBMITTED in live, do not check SL/TP yet.
                 continue

            if sym in market_data:
                curr_price = market_data[sym]
                pos['current_price'] = curr_price
                
                # Retrieve current plan state
                current_plan = pos.get('plan', 'A')
                
                if current_plan == 'A':
                    # Plan A: Active Monitoring (Standard Bracket)
                    if curr_price <= pos['sl']:
                        logger.info(f"OrderManager: Price {curr_price} hit SL {pos['sl']}. Transitioning A -> C.")
                        self.transition_to(sym, "C", "SL Hit")
                    
                    elif curr_price >= pos['tp']:
                        logger.info(f"OrderManager: Price {curr_price} hit TP {pos['tp']}. Transitioning A -> Exit.")
                        self.close_position(sym, "TP Hit")

    def transition_to(self, symbol: str, new_plan_code: str, reason: str):
        """
        Executes the State Transition Logic (The Core State Machine).
        """
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        logger.info(f"OrderManager: Transitioning {symbol} from Plan {pos.get('plan', '?')} to Plan {new_plan_code}. Reason: {reason}")
        
        # update state
        pos['plan'] = new_plan_code
        pos['plan_reason'] = reason # Persist the "Why"
        # Do NOT overwrite 'status' (FILLED) with 'EXECUTING_X'. 
        # keep standard status for broker, use 'plan' for logic.
        
        # Execute the logic for the new plan
        if new_plan_code == "C":
            # Plan C: Validation Failure / Stop Loss Hit -> Immediate Exit
            self.close_position(symbol, f"Plan C Executed: {reason}")
            
        elif new_plan_code == "J":
            # Plan J: Emergency Kill
            self.close_position(symbol, f"Plan J Executed: {reason}")

    def close_position(self, symbol: str, reason: str):
        import time
        if symbol in self.positions:
            pos = self.positions[symbol]
            logger.info(f"Closing position {symbol}. Reason: {reason}")
            
            # Calculate PnL
            exit_price = pos['current_price']
            pnl = (exit_price - pos['entry']) * pos['size']
            outcome = 1 if pnl > 0 else 0
            
            # Log Trade via ExecutionManager
            try:
                from asr_trading.execution.execution_manager import execution_manager
                # Generate a dummy plan_id or use stored order_id
                pid = pos.get('order_id', f"AUTO_{int(time.time())}")
                
                execution_manager.record_trade_result(
                    plan_id=pid,
                    strategy_id=pos.get('strategy', 'UNKNOWN'),
                    symbol=symbol,
                    pnl=pnl,
                    outcome=outcome,
                    features=pos.get('features')
                )
            except Exception as e:
                logger.error(f"OrderManager: Failed to log trade result: {e}")

            del self.positions[symbol]

order_engine = OrderManager()
