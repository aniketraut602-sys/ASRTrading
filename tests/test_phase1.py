import asyncio
import time
from asr_trading.core.avionics import avionics_monitor, telemetry
from asr_trading.core.security import audit_ledger, SecretsManager
from asr_trading.data.canonical import Tick
from asr_trading.data.feed_manager import feed_manager, FeedProvider
from asr_trading.core.logger import logger

class MockFeed(FeedProvider):
    def get_name(self):
        return "MOCK_V1"

    async def connect(self):
        pass

    async def get_latest_tick(self, symbol: str):
        return Tick(
            symbol=symbol,
            timestamp=time.time(),
            bid=100.0,
            ask=100.1,
            last=100.05,
            volume=1000,
            source="MOCK",
            sequence=1
        )

async def run_tests():
    print("--- Starting Phase 1 Verification ---")
    
    # 1. Security Test
    print("[1] Testing Security...")
    try:
        SecretsManager.get_secret("NON_EXISTENT_KEY", required=True)
    except Exception:
        print("    -> Secret validation working (Caught expected exception).")
    
    audit_ledger.record_event("TEST_START", "Tester", {"phase": 1})
    print("    -> Audit Log recorded.")

    # 2. Feed Manager Test
    print("[2] Testing Feed Manager...")
    mock = MockFeed()
    feed_manager.register_provider("PRIMARY", mock)
    
    tick = await feed_manager.get_tick("AAPL")
    print(f"    -> Fetched Tick: {tick}")
    
    if tick and tick.source == "MOCK":
        print("    -> Feed Manager wiring SUCCESS.")
    else:
        print("    -> Feed Manager wiring FAILED.")

    # 3. Avionics Test
    print("[3] Testing Avionics...")
    health = avionics_monitor.check_health()
    print(f"    -> Health Status: {health}")
    
    telemetry.record_metric("test_metric", 42.0, {"env": "test"})
    print("    -> Telemetry recorded.")
    
    print("--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(run_tests())
