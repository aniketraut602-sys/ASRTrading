from typing import List, Tuple, Optional
import statistics
from asr_trading.data.canonical import Tick
from asr_trading.core.logger import logger
from asr_trading.core.avionics import telemetry

class DataIntegrityException(Exception):
    pass

class Normalizer:
    """
    Ensures data quality by cross-validating multiple data sources.
    Implements Median-of-Three logic to filter outliers.
    """
    def __init__(self, disagreement_threshold_pct: float = 0.5):
        self.threshold = disagreement_threshold_pct

    def cross_validate(self, inputs: List[Tick]) -> Optional[Tick]:
        """
        Takes N Ticks (from different sources) for the same symbol/timestamp.
        Returns the most reliable Tick (Median price).
        """
        if not inputs:
            return None
        
        if len(inputs) == 1:
            # Only one source available - trusting it but logging warning if critical mode
            # 17.1 Audit Fix: Must validate even if single source
            if self.validate_tick(inputs[0]):
                return inputs[0]
            return None

        # Median logic on 'last' price
        sorted_ticks = sorted(inputs, key=lambda x: x.last)
        median_index = len(sorted_ticks) // 2
        median_tick = sorted_ticks[median_index]
        
        # disagreement check
        min_price = sorted_ticks[0].last
        max_price = sorted_ticks[-1].last
        
        if median_tick.last == 0:
            return None

        disagreement = ((max_price - min_price) / median_tick.last) * 100
        
        telemetry.record_metric("data.disagreement_pct", disagreement, {"symbol": median_tick.symbol})

        if disagreement > self.threshold:
            logger.warning(f"Data Normalizer: High disagreement ({disagreement:.2f}%) for {median_tick.symbol}. Sources: {[t.source for t in inputs]}")
            telemetry.record_event("data_integrity_warning", {
                "symbol": median_tick.symbol,
                "disagreement": disagreement,
                "prices": [t.last for t in inputs]
            })
            # Strict Mode for Aircraft Acceptance: Reject if > 5%
            logger.critical(f"Data Normalizer: Disagreement {disagreement:.2f}% > Threshold. REJECTING TICK (Degraded Mode).")
            telemetry.record_event("data_disagreement_reject", {"symbol": median_tick.symbol, "pct": disagreement})
            return None
            
        return median_tick

    def validate_tick(self, tick: Tick) -> bool:
        if not tick.is_valid():
            logger.error(f"Invalid tick received from {tick.source}: {tick}")
            return False
        return True

normalizer = Normalizer()
