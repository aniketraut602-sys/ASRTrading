import abc
import time
from typing import List, Optional, Dict
from asr_trading.data.canonical import Tick
from asr_trading.data.normalizer import normalizer
from asr_trading.core.logger import logger
from asr_trading.core.avionics import avionics_monitor, telemetry, CircuitBreaker
from asr_trading.core.auditor import Auditor

class FeedProvider(abc.ABC):
    @abc.abstractmethod
    def get_name(self) -> str:
        pass

    @abc.abstractmethod
    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        pass

    @abc.abstractmethod
    async def connect(self):
        pass

class FeedManager:
    """
    Orchestrates data ingestion with Triple Redundancy.
    Primary -> Secondary -> Cache.
    """
    def __init__(self):
        self.primary: Optional[FeedProvider] = None
        self.secondary: Optional[FeedProvider] = None
        self.tertiary: Optional[FeedProvider] = None
        self.local_cache_source: Dict[str, Tick] = {} 
        self.active_source = "PRIMARY"

    def register_provider(self, role: str, provider: FeedProvider):
        if role == "PRIMARY":
            self.primary = provider
        elif role == "SECONDARY":
            self.secondary = provider
        elif role == "TERTIARY":
            self.tertiary = provider
        
        avionics_monitor.register_service(f"feed_{role.lower()}_{provider.get_name()}")
        logger.info(f"FeedManager: Registered {role} provider: {provider.get_name()}")

    @CircuitBreaker(name="feed_manager_fetch")
    async def get_tick(self, symbol: str) -> Optional[Tick]:
        """
        Fetches tick with automatic failover: Primary -> Secondary -> Tertiary -> Local Cache.
        """
        tick = None
        providers = [
            ("PRIMARY", self.primary),
            ("SECONDARY", self.secondary),
            ("TERTIARY", self.tertiary)
        ]

        # Dynamic Failover Loop
        for role, provider in providers:
            # Skip if we are locked to a lower priority (unless auto-recovery logic resets active_source -- todo)
            # For "Jumbo Jet" redundancy, we generally try the highest priority that is healthy
            # OR we stick to the last working one. Let's try "Try Active, then Fallback".
            
            # Simple priority logic: Always try Primary first unless CB is open (handled by specific service CBs ideally)
            # Here we iterate priority 1 to 3. 
            
            if provider:
                try:
                    # In a real system, we'd check CircuitBreaker state before calling
                    tick = await provider.get_latest_tick(symbol)
                    if tick and tick.is_valid():
                        if tick.is_stale(threshold_sec=30.0): # Configurable threshold
                             logger.warning(f"{role} Feed ({provider.get_name()}) STALE data (Age > 30s). Rejecting.")
                             telemetry.record_event("feed_stale_rejected", {"provider": provider.get_name(), "symbol": symbol})
                             continue

                             telemetry.record_event("feed_stale_rejected", {"provider": provider.get_name(), "symbol": symbol})
                             continue
                        
                        # 17.2 Zero-Discrepancy Check
                        Auditor.audit_tick_integrity(tick)

                        avionics_monitor.heartbeat(f"feed_{role.lower()}_{provider.get_name()}")
                        self.local_cache_source[symbol] = tick # Update Hot Cache
                        return tick
                    elif tick and not tick.is_valid():
                        logger.warning(f"{role} Feed ({provider.get_name()}) returned CORRUPT data. Rejecting.")
                        telemetry.record_event("feed_corruption_rejected", {"provider": provider.get_name(), "symbol": symbol})

                except Exception as e:
                    logger.warning(f"{role} Feed ({provider.get_name()}) Failed: {e}")
                    telemetry.record_event("feed_failover", {"failed": role, "symbol": symbol})
                    continue # Try next provider

        # 4. Fallback to Cache (Replay/Stale) - HARDENED
        if tick is None:
            tick = self.local_cache_source.get(symbol)
            if tick:
                # 17.1 Audit Fix: Do not serve ancient data
                if tick.is_stale(threshold_sec=300.0): # 5 Minute hard limit for cache
                    logger.critical(f"FeedManager: Cache for {symbol} is expired (>5m). Returning None.")
                    return None
                    
                logger.warning(f"CRITICAL: Serving CACHED data for {symbol}. Market data outage!")
                telemetry.record_event("feed_outage_cache_serve", {"symbol": symbol})
                # In vNext, we mark this tick as DEGRADED validity
        
        return tick

feed_manager = FeedManager()
