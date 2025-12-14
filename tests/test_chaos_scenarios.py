import pytest
import asyncio
from asr_trading.execution.execution_manager import execution_manager, TradePlan
from asr_trading.data.feed_manager import feed_manager
from tests.chaos_monkey import ChaosProvider, ChaosBroker

# --- Harness ---

import pytest
import asyncio
from asr_trading.execution.execution_manager import execution_manager, TradePlan
from asr_trading.data.feed_manager import feed_manager
from tests.chaos_monkey import ChaosProvider, ChaosBroker

# --- Harness ---

def test_feed_failover_cascade():
    async def _run():
        """
        Scenario: Primary and Secondary feeds fail. System must fallback to Tertiary.
        """
        p1 = ChaosProvider("P1_FAIL", fail=True)
        p2 = ChaosProvider("P2_FAIL", fail=True)
        p3 = ChaosProvider("P3_OK", fail=False)
        
        feed_manager.register_provider("PRIMARY", p1)
        feed_manager.register_provider("SECONDARY", p2)
        feed_manager.register_provider("TERTIARY", p3)
        
        # Request Tick
        tick = await feed_manager.get_tick("CHAOS_SYM")
        
        assert tick is not None
        assert tick.source == "P3_OK"
    asyncio.run(_run())

def test_broker_failover():
    async def _run():
        """
        Scenario: Primary Broker fails (5xx/Timeout). Logic auto-routes to Secondary.
        """
        b1 = ChaosBroker("BROKER_A_FAIL", fail=True)
        b2 = ChaosBroker("BROKER_B_OK", fail=False)
        
        execution_manager.set_brokers(b1, b2)
        # Reset state
        execution_manager.used_plan_ids = set() 
        
        plan = TradePlan("CHAOS_PLAN_1", "SYM", "BUY", 1, 100, 99, 101, "A", "PENDING")
        
        res = await execution_manager.execute_plan(plan)
        
        assert res["status"] == "FILLED"
        assert "BROKER_B_OK" in res["order_id"]
    asyncio.run(_run())

def test_data_corruption_sanitization():
    async def _run():
        """
        Scenario: Feed returns corrupted tick (e.g. Price <= 0 or Massive spike).
        System should reject or normalize it.
        """
        class CorruptProvider(ChaosProvider):
            async def get_latest_tick(self, s):
                from asr_trading.data.canonical import Tick
                import time
                # Malicious tick: Price = -100
                return Tick(s, time.time(), -100, 100, 100, 100, self.name, 1)

        p_bad = CorruptProvider("P_BAD")
        feed_manager.register_provider("PRIMARY", p_bad)
        
        # We expect the feed manager (or risk layer, though feed manager is raw) 
        # to either pass raw data or a validation layer to catch it.
        # In Phase 9, let's assume `get_tick` has basic validation or we check if downstream handles it.
        # For now, let's just assert the raw feed returns it, and we rely on `RiskManager` to reject usage.
        
        tick = await feed_manager.get_tick("BAD_SYM")
        
        # If feed manager doesn't validate, it returns negative price.
        # If it validates, it returns None or Fallback.
        # Let's assume STRICT validation is what we want.
        
        if tick:
             # Assert our validation logic works (if implemented)
             # If not implemented, this test fails, revealing a bug (Goal of Phase 9).
             assert tick.last > 0, "System accepted negative price tick!"
    asyncio.run(_run())

def test_latency_spike():
    async def _run():
        # Stub for latency
        pass
    asyncio.run(_run())
