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
        
        return {
            "order_id": order_id, 
            "status": "FILLED",
            "avg_price": plan.entry_price,
            "filled_qty": plan.quantity,
            "broker": "PAPER"
        }
