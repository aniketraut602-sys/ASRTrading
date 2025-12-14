from typing import Dict, List, Any
from asr_trading.core.logger import logger

class RegimeClassifier:
    """
    Phase 18.5: Regime Fingerprinting.
    Classifies market state to reuse proven responses.
    State Vector: [Volatility, Trend]
    """
    def __init__(self):
        # Fingerprints: Known regimes and their preferred strategies
        # Ideally this is learned, but hard-coded priors are safer for Phase 18 start
        self.priors = {
            "LOW_VOL_BULL": ["STRAT_MOMENTUM_V1", "STRAT_TREND_FOLLOW"],
            "HIGH_VOL_BULL": ["STRAT_SCALP_HAMMER"], # Quick scalps only
            "LOW_VOL_BEAR": ["STRAT_MOMENTUM_SHORT"],
            "HIGH_VOL_BEAR": ["STRAT_SCALP_HAMMER"], # Counter-trend scalps
            "HIGH_VOL_SIDEWAYS": ["STRAT_GRID", "STRAT_SCALP_HAMMER"],
            "LOW_VOL_SIDEWAYS": [] # Do nothing (Dead market)
        }

    def detect_regime(self, features: Dict[str, float]) -> str:
        """
        Returns regime ID string.
        """
        # 1. Volatility
        vol = features.get("Volatility", 0.0)
        atr = features.get("ATR", 0.0)
        
        # Volatility Thresholds (Need calibration)
        if vol < 0.001: vol_state = "LOW_VOL"
        elif vol > 0.004: vol_state = "HIGH_VOL"
        else: vol_state = "MED_VOL" # Treated same as Low/High depending on context? 
        # For simplicity, map MED to LOW or separate. 
        # Let's map MED -> "LOW" for safety, or just keep strict buckets.
        
        # 2. Trend
        # Use SMA50 slope or price vs SMA50
        price = features.get("close", 0) # Feature engine normally passes last close
        # If not in features, we can't judge. But features usually have 'SMA_50'.
        
        sma50 = features.get("SMA_50", 0)
        macd = features.get("MACD", 0)
        
        if sma50 > 0:
             if macd > 0 and price > sma50: trend_state = "BULL"
             elif macd < 0 and price < sma50: trend_state = "BEAR"
             else: trend_state = "SIDEWAYS"
        else:
            trend_state = "SIDEWAYS" # Default
            
        regime_id = f"{vol_state}_{trend_state}"
        
        # logger.debug(f"Regime Detected: {regime_id}")
        return regime_id

    def get_preferred_strategies(self, regime_id: str) -> List[str]:
        return self.priors.get(regime_id, [])

regime_monitor = RegimeClassifier()
