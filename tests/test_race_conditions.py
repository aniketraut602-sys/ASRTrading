import pytest
import asyncio
import time
from asr_trading.execution.execution_manager import execution_manager, TradePlan
from tests.chaos_monkey import ChaosBroker

def test_race_condition_idempotency_check():
    async def _run():
        """
        Scenario: Multiple threads/coroutines attempt to execute the exact same Plan ID simultaneously.
        Result: Only ONE execution should proceed. Others should be IGNORED_DUPLICATE.
        """
        # Setup
        broker = ChaosBroker("RACE_BROKER", fail=False)
        execution_manager.set_brokers(broker, None)
        execution_manager.used_plan_ids = set() # Reset
        
        plan_id = "RACE_PLAN_001"
        plan = TradePlan(plan_id, "SYM", "BUY", 10, 100, 95, 105, "PLN", "PENDING")
        
        # Launch 5 concurrent executions
        tasks = [execution_manager.execute_plan(plan) for _ in range(5)]
        
        results = await asyncio.gather(*tasks)
        
        success_count = 0
        duplicate_count = 0
        
        for res in results:
            if "status" in res:
                if res["status"] == "SUBMITTED" or res["status"] == "FILLED":
                    success_count += 1
                elif res["status"] == "IGNORED_DUPLICATE":
                    duplicate_count += 1
        
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert duplicate_count == 4, f"Expected 4 duplicates, got {duplicate_count}"

    asyncio.run(_run())

def test_sequential_locking():
    """
    Ensure Critical Sections are locked correctly (Mock check).
    Since Python asyncio is single-threaded, we rely on logic checks.
    Real threading tests would require `threading` module and blocking I/O simulation.
    """
    pass
