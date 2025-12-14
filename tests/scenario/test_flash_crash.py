import unittest
import asyncio
from unittest.mock import MagicMock
from asr_trading.execution.risk_manager import risk_manager
from asr_trading.strategy.selector import strategy_selector
from asr_trading.core.logger import logger

class TestFlashCrash(unittest.TestCase):
    def test_risk_halt_on_crash(self):
        """
        Simulate a Flash Crash where PnL drops 5% instantly.
        RiskManager should HALT.
        """
        # 1. Setup Risk Manager with 10k capital
        risk_manager.total_capital = 10000.0
        risk_manager.current_daily_loss = 0.0
        risk_manager.profile.max_daily_loss_pct = 0.03 # 3% limit
        
        # 2. Simulate massive loss (e.g. Long position crashes)
        loss_amount = 500.0 # 5% loss
        risk_manager.record_loss(loss_amount)
        
        # 3. Verify Halt
        check = risk_manager.check_trade("AAPL", 150.0, "STRAT_ANY", 0.9)
        print(f"\n[Scenario] Flash Crash Risk Check: {check}")
        
        self.assertFalse(check["allowed"], "Risk Manager should BLOCK trades after Flash Crash")
        self.assertIn("Daily Loss Limit", check["reason"])

    def test_selector_reaction(self):
        """
        Simulate RSI diving to 5 (extreme crash).
        Strategy should either Buy the Dip OR Stay Out (depending on rules).
        For this test, checking that it doesn't CRASH.
        """
        features = {"RSI": 5.0, "MACD": -2.0, "Volatility": 0.05} # Extreme
        patterns = [] 
        knowledge = []
        
        proposal = strategy_selector.select_strategy("TSLA", features, patterns, knowledge)
        # It might return None or a Mean Reversion strategy
        if proposal:
            print(f"\n[Scenario] Selector proposed during crash: {proposal.strategy_id}")
        else:
            print(f"\n[Scenario] Selector stayed safe (None).")
            
        # Assertion: Code ran without error
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
