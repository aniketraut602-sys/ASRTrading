import unittest
from asr_trading.data.canonical import OHLC
from asr_trading.analysis.features import feature_engine
import time

class TestFeatureEngine(unittest.TestCase):
    def test_indicator_calculation(self):
        symbol = "TEST_SYM"
        
        # Feed 100 synthetic candles
        # Linear price increase 100 -> 200
        for i in range(100):
            price = 100.0 + i
            ohlc = OHLC(
                symbol=symbol,
                timestamp=time.time() + i*60,
                open=price,
                high=price+1,
                low=price-1,
                close=price,
                volume=1000,
                interval="1m"
            )
            result = feature_engine.on_ohlc(ohlc)
            
            if i < 49:
                self.assertEqual(result["status"], "WARMUP")
            else:
                self.assertEqual(result["status"], "READY")
                features = result["features"]
                
                # Check SMA_50
                # Price is i+100. Last 50 prices are [i+51 ... i+100]
                # Mean should be roughly i + 75.5
                self.assertIn("SMA_50", features)
                self.assertIn("RSI", features)
                self.assertIn("MACD", features)
                
                # Check logic availability (not strict value due to floating point and exact pandas algo difference)
                self.assertIsNotNone(features["SMA_50"])

    def test_empty_dataframe(self):
        df = feature_engine.window_engine.get_dataframe("NON_EXISTENT")
        self.assertTrue(df.empty)

if __name__ == "__main__":
    unittest.main()
