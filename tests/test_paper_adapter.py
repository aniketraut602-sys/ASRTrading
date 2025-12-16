import asyncio
import json
import dataclasses
from asr_trading.execution.paper_adapter import PaperAdapter
from asr_trading.strategy.planner import TradePlan

async def test():
    print("Initializing...")
    adapter = PaperAdapter()
    
    plan = TradePlan(
        plan_id="TEST_PLAN_1",
        symbol="NIFTY_TEST",
        side="BUY",
        quantity=10,
        limit_price=100.0,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=102.0,
        plan_code="MANUAL_TEST",
        status="PENDING",
        confidence=0.9
    )
    
    print("Placing Order...")
    try:
        res = await adapter.place_order(plan)
        print(f"Result: {res}")
        
        print("Testing Serialization...")
        dumped = json.dumps(res)
        print(f"Serialized: {dumped}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test())
