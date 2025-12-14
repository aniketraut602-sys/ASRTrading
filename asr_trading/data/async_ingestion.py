import asyncio
# import yfinance as yf (Sync, so maybe run in threadpool)
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
import random

class CircuitBreakerOpen(Exception):
    pass

class BaseProvider:
    def __init__(self, name):
        self.name = name
        self.failures = 0
        self.threshold = 3
        self.state = "CLOSED" # CLOSED, OPEN (failing), HALF-OPEN
        
    async def get_price(self, symbol: str) -> float:
        if self.state == "OPEN":
            # Simple retry logic could go here (e.g. timeout)
            raise CircuitBreakerOpen(f"{self.name} is OPEN")
        
        try:
            price = await self._fetch(symbol)
            self.failures = 0
            return price
        except Exception as e:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit Breaker OPEN for {self.name}")
            raise e

    async def _fetch(self, symbol: str) -> float:
        raise NotImplementedError

class YahooProvider(BaseProvider):
    def __init__(self):
        super().__init__("Yahoo")

    async def _fetch(self, symbol: str) -> float:
        # Simulate Async wrapper for yfinance
        # In prod: loop.run_in_executor
        import yfinance as yf
        return await asyncio.to_thread(self._sync_fetch, symbol)

    def _sync_fetch(self, symbol):
        ticker = yf.Ticker(symbol)
        # Fast history - Changed to 1m for Phase 17.1 Audit
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty: raise ValueError("No data")
        return hist['Close'].iloc[-1]

# 19.3 Cleanup: Removed AlphaVantage Mock Provider (Use Yahoo or Polygon)

class DataNexus:
    def __init__(self):
        # 19.3 Cleanup: Removed Mock Sources
        self.providers = [YahooProvider()]
    
    async def get_live_price(self, symbol: str) -> float:
        errors = []
        for provider in self.providers:
            try:
                price = await provider.get_price(symbol)
                return price
            except CircuitBreakerOpen:
                continue
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                errors.append(e)
        
        raise RuntimeError(f"All providers failed for {symbol}: {errors}")

data_nexus = DataNexus()
