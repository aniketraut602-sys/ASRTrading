import unittest
from unittest.mock import MagicMock, patch
from asr_trading.brain.governance import governance
from asr_trading.execution.risk_manager import risk_manager
from asr_trading.brain.trust import trust_system
from asr_trading.strategy.selector import strategy_selector
from asr_trading.brain.regime import regime_monitor

class TestPhase18Survival(unittest.TestCase):
    
    def test_governance_blocking(self):
        """
        Verify that a 'RETIRED' strategy is blocked by selector.
        """
        print("\n[Phase 18] Testing Governance Blocking...")
        
        # 1. Force Retire in Stats
        governance.stats["STRAT_SCALP_HAMMER"] = {"status": "RETIRED", "history": [0]*50, "trades": 50, "wins": 0}
        
        # 2. Setup Features that WOULD trigger Hammer
        features = {"RSI": 30.0, "MACD": 0.0, "Volatility": 0.001}
        # Fake pattern
        from asr_trading.analysis.patterns import DetectedPattern
        patterns = [DetectedPattern("CDL_HAMMER", "Hammer", "AAPL", 1000, 0.9, "BULLISH", {})]
        
        # 3. Select
        proposal = strategy_selector.select_strategy("AAPL", features, patterns, [])
        
        # 4. Assert None (Blocked)
        if proposal is None:
             print("[PASS] Selector correctly blocked RETIRED strategy.")
        else:
             self.assertNotEqual(proposal.strategy_id, "STRAT_SCALP_HAMMER", "Selector proposed a RETIRED strategy!")

    def test_risk_scaling(self):
        """
        Verify RiskManager reduces size on High Volatility and Low Trust.
        """
        print("\n[Phase 18] Testing Risk Scaling...")
        
        # Reset Risk Manager Constraints
        risk_manager.total_capital = 100000.0 # 100k Capital -> 2k Risk per trade -> 20 shares at 100
        risk_manager.current_daily_loss = 0.0
        
        # Mock Trust to 1.0 (Neutral/High) to test Volatility in isolation
        with patch.object(trust_system, 'get_sizing_scalar', return_value=1.0):
            # Base Case (Low Vol, Normal Trust)
            base_check = risk_manager.check_trade("AAPL", 100.0, "STRAT_TEST", 0.9, volatility=0.001)
            base_qty = base_check["max_size"]
            print(f"Base Qty: {base_qty}")
            
            # Case A: High Volatility (Should reduce)
            vol_check = risk_manager.check_trade("AAPL", 100.0, "STRAT_TEST", 0.9, volatility=0.02) # 2% Vol (High)
            vol_qty = vol_check["max_size"]
            print(f"High Vol Qty: {vol_qty}")
            self.assertTrue(vol_qty < base_qty, f"RiskManager did not reduce size for High Vol (Base={base_qty}, Vol={vol_qty})")
        
        # Case B: Low Trust (Should reduce from Base)
        # Mock Trust Score Low
        with patch.object(trust_system, 'get_sizing_scalar', return_value=0.4): # Skeptical
             trust_check = risk_manager.check_trade("AAPL", 100.0, "STRAT_TEST", 0.9, volatility=0.001)
             trust_qty = trust_check["max_size"]
             print(f"Low Trust Qty: {trust_qty}")
             self.assertTrue(trust_qty < base_qty, f"RiskManager did not reduce size for Low Trust (Base={base_qty}, Trust={trust_qty})")

if __name__ == '__main__':
    unittest.main()
