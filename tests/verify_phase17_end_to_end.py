import asyncio
import unittest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock, patch

# Core Modules
from asr_trading.data.canonical import Tick
from asr_trading.data.feed_manager import feed_manager
from asr_trading.analysis.features import feature_engine
from asr_trading.strategy.selector import strategy_selector
from asr_trading.strategy.planner import planner_engine
from asr_trading.execution.execution_manager import execution_manager
from asr_trading.core.auditor import Auditor, InvariantViolation

class TestPhase17Final(unittest.TestCase):
    
    def test_end_to_end_flow(self):
        """
        Simulate the entire pipeline.
        Tick -> Feature -> Strategy -> Plan -> Execution
        """
        print("\n[Phase 17] Starting End-to-End Verification...")
        
        # 1. Ingest Tick (Simulated)
        # 17.10 Verification Fix: Strict Tick creation
        tick = Tick(symbol="AAPL", last=150.0, timestamp=1000, volume=500, source="TEST", bid=149.9, ask=150.1, sequence=101)
        # Audit Tick
        Auditor.audit_tick_integrity(tick)
        print("[Check 1] Tick Integrity: PASS")
        
        # 2. Generate Features
        # Mocking OHLC ingestion for window
        # Pushing 50 mock candles to warmup
        for i in range(50):
            from asr_trading.data.canonical import OHLC
            feature_engine.on_ohlc(OHLC("AAPL", 1000+i, 150, 155, 149, 150, 100, interval="1m"))
            
        result = feature_engine.on_ohlc(OHLC("AAPL", 2000, 150, 155, 149, 150, 100, interval="1m"))
        self.assertEqual(result["status"], "READY")
        features = result["features"]
        print(f"[Check 2] Feature Generation: PASS (Keys: {len(features)})")
        
        # 3. Strategy Selection
        # Force RSI to be low to trigger HAMMER logic if pattern existed (mocking pattern)
        features["RSI"] = 30.0 
        from asr_trading.analysis.patterns import DetectedPattern
        # 17.10 Verification Fix: Strict Pattern creation
        # pattern_id, name, symbol, timestamp, confidence, side, evidence
        patterns = [DetectedPattern(
            pattern_id="CDL_HAMMER", 
            name="Hammer", 
            symbol="AAPL", 
            timestamp=2000, 
            confidence=0.9, 
            side="BULLISH", 
            evidence={"src": "mock"}
        )]
        
        proposal = strategy_selector.select_strategy("AAPL", features, patterns, [])
        self.assertIsNotNone(proposal)
        print(f"[Check 3] Strategy Selection: PASS (Proposed: {proposal.strategy_id})")
        
        # 4. Planning (UUID + Confidence)
        plan = planner_engine.create_plan(proposal, 150.0)
        self.assertIsNotNone(plan)
        self.assertTrue(len(plan.plan_id) > 10, "Plan ID should be UUID")
        self.assertEqual(plan.confidence, proposal.confidence, "Confidence lost in translation")
        print(f"[Check 4] Planning: PASS (ID: {plan.plan_id})")
        
        # 5. Execution (Auditor Gate)
        # Mocking broker
        mock_broker = MagicMock()
        mock_broker.get_name.return_value = "MOCK_BROKER"
        mock_broker.place_order = AsyncMock(return_value={"status": "FILLED"})
        execution_manager.set_brokers(mock_broker, None)
        
        # Run Async Execution
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(execution_manager.execute_plan(plan))
        
        self.assertEqual(res["status"], "FILLED")
        print("[Check 5] Execution: PASS")
        
        print("\n[Phase 17] FAILURE-FREE DOUBLE SCAN COMPLETE.")

if __name__ == '__main__':
    # Suppress Logs for clean output
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    unittest.main()
