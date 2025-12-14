import unittest
import pandas as pd
import time
from asr_trading.data.canonical import OHLC
from asr_trading.analysis.features import feature_engine
from asr_trading.analysis.patterns import pattern_detector
from asr_trading.brain.knowledge import knowledge_manager

class TestPhase3Full(unittest.TestCase):
    def test_pipeline(self):
        print("--- Testing Feature -> Pattern -> Knowledge Pipeline ---")
        
        # 1. Feed Feature Engine
        symbol = "PIPELINE_TEST"
        features_ready = False
        
        # Feed enough candles to warmup
        for i in range(60):
            price = 100
            # Create a Hammer at the end
            if i == 59:
                # Hammer: Open=100, Low=90, High=100.2, Close=100.2
                open_ = 100.0
                low = 90.0
                high = 100.2
                close = 100.2
                # Check Hammer Logic: Range=10.5, Body=0.2. Body <= Range*0.1? No, 0.2 <= 1.05. Yes.
                # Lower Shadow = 10. (2*Body = 0.4). Yes.
            else:
                open_ = price
                low = price
                high = price
                close = price
            
            ohlc = OHLC(
                symbol=symbol,
                timestamp=time.time() + i*60,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=1000,
                interval="1m"
            )
            res = feature_engine.on_ohlc(ohlc)
            if res["status"] == "READY":
                features_ready = True
        
        self.assertTrue(features_ready, "Feature Engine failed to warmup")
        print("    -> Feature Engine: READY")
        
        # 2. Get DataFrame & Detect Patterns
        df = feature_engine.window_engine.get_dataframe(symbol)
        patterns = pattern_detector.analyze(df, symbol)
        
        found_hammer = False
        for p in patterns:
            print(f"    -> Detected Pattern: {p.name} ({p.side})")
            if p.pattern_id == "CDL_HAMMER":
                found_hammer = True
                
                # 3. Query Knowledge
                k_items = knowledge_manager.query([p.pattern_id])
                print(f"       -> Knowledge Items Found: {len(k_items)}")
                for k in k_items:
                    print(f"          - {k['title']}: {k['summary']}")
                self.assertTrue(len(k_items) > 0, "Knowledge Manager returned no context for Hammer")

        self.assertTrue(found_hammer, "Pattern Detector failed to see Hammer")
        print("--- Phase 3 Pipeline Verified ---")

if __name__ == "__main__":
    unittest.main()
