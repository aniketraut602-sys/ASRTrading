import unittest
import pandas as pd
from asr_trading.analysis.patterns import pattern_detector

class TestPatternDetector(unittest.TestCase):
    def test_doji_detection(self):
        # Create a synthetic Doji candle
        # Open=100, Close=100.1, High=105, Low=95 (Big range, tiny body)
        data = [
            {"open": 90, "high": 92, "low": 88, "close": 91, "timestamp": 1000}, # Setup
            {"open": 91, "high": 93, "low": 89, "close": 92, "timestamp": 1001}, # Setup
            {"open": 92, "high": 94, "low": 90, "close": 93, "timestamp": 1002}, # Setup
            {"open": 93, "high": 95, "low": 91, "close": 94, "timestamp": 1003}, # Setup
            {"open": 100.0, "high": 105.0, "low": 95.0, "close": 100.1, "timestamp": 1004} # DOJI
        ]
        df = pd.DataFrame(data)
        
        patterns = pattern_detector.analyze(df, "TEST_SYM")
        
        found_doji = any(p.pattern_id == "CDL_DOJI" for p in patterns)
        self.assertTrue(found_doji, "Failed to detect synthetic Doji")

    def test_engulfing_bullish(self):
        # Prev: Red candle (Open 100, Close 90)
        # Curr: Green candle (Open 89, Close 101) - Engulfs
        data = [
            {"open": 90, "high": 92, "low": 88, "close": 91, "timestamp": 1000},
            {"open": 91, "high": 93, "low": 89, "close": 92, "timestamp": 1001},
            {"open": 92, "high": 94, "low": 90, "close": 93, "timestamp": 1002},
            {"open": 100.0, "high": 102.0, "low": 88.0, "close": 90.0, "timestamp": 1003}, # Red
            {"open": 89.0, "high": 103.0, "low": 88.0, "close": 101.0, "timestamp": 1004}  # Green Engulfing
        ]
        df = pd.DataFrame(data)
        
        patterns = pattern_detector.analyze(df, "TEST_SYM")
        found_engulfing = any(p.pattern_id == "CDL_ENGULFING_BULL" for p in patterns)
        self.assertTrue(found_engulfing, "Failed to detect Bullish Engulfing")

if __name__ == "__main__":
    unittest.main()
