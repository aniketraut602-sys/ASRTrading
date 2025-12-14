from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
import time

@dataclass(frozen=True)
class Tick:
    """
    Immutable representation of a market tick.
    Used for canonical data exchange between Ingest -> Normalizer -> Strategy.
    """
    symbol: str
    timestamp: float  # Unix timestamp (UTC)
    bid: float
    ask: float
    last: float
    volume: int
    source: str       # "FINNHUB", "ALPHA_VANTAGE", "TWELVE_DATA"
    sequence: int     # Monotonically increasing ID from source (or generated)
    
    # Metadata for tracing
    received_at: float = field(default_factory=time.time)

    @property
    def datetime_utc(self):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    def is_stale(self, threshold_sec: float = 10.0) -> bool:
        """Checks if tick is older than threshold."""
        age = time.time() - self.timestamp
        return age > threshold_sec

    def is_valid(self) -> bool:
        """Basic sanity check."""
        return (
            self.bid > 0 and 
            self.ask > 0 and 
            self.last > 0 and 
            self.bid <= self.ask and
            self.volume >= 0
        )

@dataclass(frozen=True)
class OHLC:
    """
    Canonical OHLC bar.
    """
    symbol: str
    timestamp: float # Open time
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str    # "1m", "5m", "1h", "1d"
