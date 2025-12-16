import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from asr_trading.data.canonical import OHLC
from asr_trading.core.logger import logger

@dataclass
class DetectedPattern:
    pattern_id: str
    name: str
    symbol: str
    timestamp: float
    confidence: float
    side: str # "BULLISH" or "BEARISH" or "NEUTRAL"
    evidence: Dict[str, Any]

class CandleMatcher:
    """
    Deterministic Candlestick Pattern Logic.
    """
    @staticmethod
    def is_doji(open, high, low, close) -> bool:
        body = abs(close - open)
        range_ = high - low
        return range_ > 0 and body <= (range_ * 0.1)

    @staticmethod
    def is_hammer(open, high, low, close) -> bool:
        body = abs(close - open)
        range_ = high - low
        lower_shadow = min(open, close) - low
        upper_shadow = high - max(open, close)
        return range_ > 0 and lower_shadow >= (2 * body) and upper_shadow <= (body * 0.2)

    @staticmethod
    def detect(df: pd.DataFrame) -> List[Dict]:
        """
        Runs logic on the LAST row of the dataframe.
        Returns list of pattern dicts.
        """
        if len(df) < 5: return []
        
        patterns = []
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Safe Accessor
        def get_val(row, key):
             # Try Title Case (yfinance/pandas-ta) then Lower Case
             if hasattr(row, key.title()): return getattr(row, key.title())
             if hasattr(row, key.lower()): return getattr(row, key.lower())
             # Try dictionary/Series index
             if key.title() in row: return row[key.title()]
             if key.lower() in row: return row[key.lower()]
             return 0.0

        O = get_val(curr, "open")
        H = get_val(curr, "high")
        L = get_val(curr, "low")
        C = get_val(curr, "close")
        
        prev_O = get_val(prev, "open")
        prev_C = get_val(prev, "close")
        
        # Doji
        if CandleMatcher.is_doji(O, H, L, C):
            patterns.append({"id": "CDL_DOJI", "name": "Doji", "side": "NEUTRAL", "conf": 0.6})

        # Hammer (Bullish)
        if CandleMatcher.is_hammer(O, H, L, C):
            patterns.append({"id": "CDL_HAMMER", "name": "Hammer", "side": "BULLISH", "conf": 0.7})

        # Engulfing
        # Bullish: Prev Red, Curr Green, Curr Open < Prev Close, Curr Close > Prev Open
        if (prev_C < prev_O) and (C > O):
            if (O <= prev_C) and (C >= prev_O):
                patterns.append({"id": "CDL_ENGULFING_BULL", "name": "Bullish Engulfing", "side": "BULLISH", "conf": 0.8})
        
        # Bearish Engulfing
        if (prev_C > prev_O) and (C < O):
             if (O >= prev_C) and (C <= prev_O):
                patterns.append({"id": "CDL_ENGULFING_BEAR", "name": "Bearish Engulfing", "side": "BEARISH", "conf": 0.8})

        return patterns

class PatternDetector:
    """
    Orchestrator for Pattern Detection.
    """
    def __init__(self):
        self.matcher = CandleMatcher()

    def analyze(self, df: pd.DataFrame, symbol: str) -> List[DetectedPattern]:
        if df.empty:
            return []
        
        raw_patterns = self.matcher.detect(df)
        results = []
        
        timestamp = df.iloc[-1]['timestamp'] if 'timestamp' in df else 0.0

        for p in raw_patterns:
            dp = DetectedPattern(
                pattern_id=p["id"],
                name=p["name"],
                symbol=symbol,
                timestamp=timestamp,
                confidence=p["conf"],
                side=p["side"],
                evidence={"src": "rule_based"}
            )
            results.append(dp)
        
        return results

pattern_detector = PatternDetector()
