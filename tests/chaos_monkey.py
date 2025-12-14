import asyncio
import time
from asr_trading.data.feed_manager import feed_manager, FeedProvider
from asr_trading.execution.execution_manager import execution_manager, BrokerAdapter, TradePlan
from asr_trading.data.canonical import Tick
from asr_trading.core.logger import logger

# --- MOCKS ---
class ChaosProvider(FeedProvider):
    def __init__(self, name, fail=False): 
        self.name = name
        self.fail = fail
    def get_name(self): return self.name
    async def connect(self): pass
    async def get_latest_tick(self, s):
        if self.fail: raise Exception(f"CHAOS: {self.name} Down")
        return Tick(s, time.time(), 100, 101, 100.5, 100, self.name, 1)

class ChaosBroker(BrokerAdapter):
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
    def get_name(self): return self.name
    async def place_order(self, plan):
        if self.fail: raise Exception(f"CHAOS: {self.name} Rejected")
        return {"order_id": f"ORD_{self.name}", "status": "FILLED"}

async def run_chaos_scenarios():
    print("=== CHAOS MONKEY: INITIATING SYSTEM STRESS TEST ===")
    
    # SCENARIO 1: Feed Cascade
    print("\n[Scenario 1] Feed Provider Cascade Failure")
    p1 = ChaosProvider("P1", fail=True)
    p2 = ChaosProvider("P2", fail=True)
    p3 = ChaosProvider("P3", fail=False) # Only 3rd works
    
    feed_manager.register_provider("PRIMARY", p1)
    feed_manager.register_provider("SECONDARY", p2)
    feed_manager.register_provider("TERTIARY", p3)
    
    tick = await feed_manager.get_tick("CHAOS_SYM")
    if tick and tick.source == "P3":
        print("[PASS]: Cascade P1->P2->P3 success.")
    else:
        print(f"[FAIL]: Expected P3, got {tick.source if tick else 'None'}")

    # SCENARIO 2: Broker Failover
    print("\n[Scenario 2] Execution Broker Failover")
    b1 = ChaosBroker("BROKER_PRIMARY", fail=True)
    b2 = ChaosBroker("BROKER_SECONDARY", fail=False)
    
    execution_manager.set_brokers(b1, b2)
    plan = TradePlan("CHAOS_PLAN", "SYM", "BUY", 1, 100, 99, 101, "A", "PENDING")
    
    res = await execution_manager.execute_plan(plan)
    if res["status"] == "FILLED" and "BROKER_SECONDARY" in res["order_id"]:
        print("[PASS]: Failed Primary -> Secondary Broker Executed.")
    else:
        print(f"[FAIL]: {res}")

    # SCENARIO 3: Latency / Timeout (Simulated via CircuitBreaker interaction?)
    # For now, we trust the CB unit tests.
    
    print("\n=== Chaos Testing Complete ===")

if __name__ == "__main__":
    asyncio.run(run_chaos_scenarios())
