import asyncio
import sys
import os

# Add root to pythonpath
sys.path.append(os.getcwd())

from unittest.mock import MagicMock
from asr_trading.execution.groww_adapter import GrowwAdapter
from asr_trading.execution.order_manager import OrderManager, order_engine
from asr_trading.strategy.planner import TradePlan
from asr_trading.core.logger import logger

# Mute logger for cleaner test output
logger.setLevel("CRITICAL")

async def test_groww_order_lifecycle():
    print("Starting Test: Groww Lifecycle")
    
    # 1. Setup Mock Adapter
    adapter = GrowwAdapter()
    adapter.client = MagicMock()
    adapter.connected = True
    
    # Mock Place Order
    adapter.client.place_order.return_value = {"order_id": "GROWW_123"}
    
    # Mock Get Order Status (Side Effect for sequential calls)
    # Sequence: PENDING (Acknowledged) -> OPEN -> COMPLETE (Filled)
    # NOTE: Adapter converts 'REQUESTED' -> 'SUBMITTED'
    adapter.client.get_order.side_effect = [
        {"orderId": "GROWW_123", "status": "REQUESTED"}, 
        {"orderId": "GROWW_123", "status": "OPEN"},      
        {"orderId": "GROWW_123", "status": "COMPLETE", "filledQty": 10, "avgPrice": 2510.5}   
    ]
    
    # 2. Execute Plan
    plan = TradePlan(
        plan_id="TEST_PLAN_1",
        symbol="RELIANCE",
        side="BUY",
        quantity=10,
        limit_price=2500,
        stop_loss=2480,
        take_profit=2550,
        plan_code="A",
        status="PENDING"
    )
    
    # Place Order
    res = await adapter.place_order(plan)
    if res["status"] != "SUBMITTED":
        print(f"FAIL: Place order status mismatch. Got {res['status']}")
        return
        
    print(f"Order Placed: {res}")

    # 3. Register in OrderManager
    order_engine.positions.clear() # Reset
    order_engine.register_execution(plan, res["order_id"])
    
    # Initial Internal State should be OPEN (legacy) or SUBMITTED if registered carefully.
    # Currently register_execution sets status="OPEN".
    # BUT logic in monitor_lifecycle checks for ["SUBMITTED", "OPEN", "PARTIALLY_FILLED"]
    # So it should pick it up.
    
    # Configure ExecutionManager (The Singleton)
    from asr_trading.execution.execution_manager import execution_manager
    execution_manager.set_brokers(adapter, None)
    
    # 4. Loop 1: Check Submitted
    await order_engine.update_positions({}) 
    status = order_engine.positions["RELIANCE"]["status"]
    print(f"Loop 1 Status: {status}")
    if status != "SUBMITTED":
         print("FAIL: Expected SUBMITTED")
         # Note: My mock returns REQUESTED which maps to SUBMITTED.
         return

    # Loop 2: Check Open
    await order_engine.update_positions({}) 
    status = order_engine.positions["RELIANCE"]["status"]
    print(f"Loop 2 Status: {status}")
    if status != "OPEN":
         print("FAIL: Expected OPEN")
         return

    # Loop 3: Check Filled
    await order_engine.update_positions({}) 
    status = order_engine.positions["RELIANCE"]["status"]
    print(f"Loop 3 Status: {status}")
    if status != "FILLED":
         print("FAIL: Expected FILLED")
         return
         
    # Check Price Update
    entry = order_engine.positions["RELIANCE"]["entry"]
    if entry != 2510.5:
        print(f"FAIL: Entry price not updated. Got {entry}")
        return

    print("SUCCESS: Groww Lifecycle Test Passed.")

if __name__ == "__main__":
    asyncio.run(test_groww_order_lifecycle())
