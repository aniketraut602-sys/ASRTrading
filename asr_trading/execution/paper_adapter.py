from asr_trading.execution.execution_manager import BrokerAdapter
from asr_trading.strategy.planner import TradePlan
from asr_trading.core.logger import logger
import uuid
import asyncio

class PaperAdapter(BrokerAdapter):
    """
    Simulates a broker for Paper Trading execution.
    """
    def get_name(self) -> str: 
        return "PAPER_BROKER"
    
    async def place_order(self, plan: TradePlan):
        """
        Simulate order placement.
        """
        # Simulate network latency
        await asyncio.sleep(0.1)
        
        order_id = f"PAPER_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"PaperAdapter: [SIMULATION] {plan.side} {plan.quantity} {plan.symbol} @ {plan.entry_price}")
        
        # Ledger Update
        from asr_trading.core.cockpit import cockpit
        cost = float(plan.entry_price) * int(plan.quantity)
        
        if plan.side == "BUY":
            cockpit.balance_available -= cost
            cockpit.margin_used += cost # Simplified margin tracking
        elif plan.side == "SELL":
            cockpit.balance_available += cost
            cockpit.margin_used -= cost
            if cockpit.margin_used < 0: cockpit.margin_used = 0
            
        return {
            "order_id": order_id, 
            "status": "FILLED",
            "avg_price": float(plan.entry_price),
            "filled_qty": int(plan.quantity),
            "broker": "PAPER"
        }

    async def get_balance(self) -> float:
        # For paper, return the internal tracked balance
        from asr_trading.core.cockpit import cockpit
        return cockpit.balance_available
