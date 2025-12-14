import unittest
import asyncio
import time
from asr_trading.analysis.patterns import DetectedPattern
from asr_trading.brain.knowledge import knowledge_manager
from asr_trading.strategy.selector import strategy_selector
from asr_trading.strategy.planner import planner_engine
from asr_trading.execution.execution_manager import execution_manager, BrokerAdapter, TradePlan

# Mock Broker
class MockBroker(BrokerAdapter):
    def get_name(self): return "MOCK_BROKER"
    async def place_order(self, plan: TradePlan):
        return {"order_id": "MOCK_FAIL", "status": "FAILED"}

class MockBrokerSuccess(BrokerAdapter):
    def get_name(self): return "MOCK_SUCCESS"
    async def place_order(self, plan: TradePlan):
        return {"order_id": f"ORD_{plan.plan_id}", "status": "FILLED"}

class TestPhase4Full(unittest.TestCase):
    def test_full_chain(self):
        print("--- Testing Strategy -> Planner -> Execution Chain ---")
        
        # 1. Simulate Inputs (Hammer Pattern detected)
        symbol = "PHASE4_TEST"
        patterns = [
            DetectedPattern(
                pattern_id="CDL_HAMMER",
                name="Hammer",
                symbol=symbol,
                timestamp=time.time(),
                confidence=0.8,
                side="BULLISH",
                evidence={}
            )
        ]
        
        features = {"RSI": 35.0, "MACD": -0.5} # Oversold RSI supports Hammer
        
        knowledge = knowledge_manager.query(["CDL_HAMMER"])
        
        # 2. Strategy Selector
        proposal = strategy_selector.select_strategy(symbol, features, patterns, knowledge)
        
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.action, "BUY")
        self.assertEqual(proposal.strategy_id, "STRAT_SCALP_HAMMER")
        print(f"    -> Strategy Selected: {proposal.strategy_id}")
        
        # 3. Planner (Risk Check + Plan Creation)
        current_price = 100.0
        plan = planner_engine.create_plan(proposal, current_price)
        
        self.assertIsNotNone(plan)
        self.assertEqual(plan.plan_code, "A")
        self.assertTrue(plan.quantity > 0)
        print(f"    -> Plan Created: Plan {plan.plan_code}, Buy {plan.quantity} @ {plan.limit_price}")
        
        # 4. Execution Manager
        # Configure Mocks
        execution_manager.set_brokers(MockBrokerSuccess(), MockBrokerSuccess())
        
        # Run Async Execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execution_manager.execute_plan(plan))
        
        self.assertEqual(result["status"], "FILLED")
        print(f"    -> Execution Result: {result}")
        print("--- Phase 4 Chain Verified ---")

if __name__ == "__main__":
    unittest.main()
