from typing import Optional
import time
from asr_trading.data.feed_manager import FeedProvider
from asr_trading.data.canonical import Tick
from asr_trading.core.logger import logger

# Try importing real SDK
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

class YahooFinanceProvider(FeedProvider):
    def __init__(self):
        self.tickers = {}

    def get_name(self) -> str:
        return "YAHOO_FINANCE"

    async def connect(self):
        if not HAS_YF:
            logger.error("yfinance not installed. Please `pip install yfinance`.")
        else:
            logger.info("YahooFinanceProvider: Ready (Stateless).")

    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        if not HAS_YF:
            return None
            
        try:
            # yfinance fetch
            # Note: yf.Ticker(sys).history(period="1d", interval="1m") is blocking.
            # In production asyncio, run in executor.
            ticker = yf.Ticker(symbol)
            # Get just the last row of 1m data
            df = ticker.history(period="1d", interval="1m")
            
            if df.empty:
                return None
                
                
            last_row = df.iloc[-1]
            ts = last_row.name
            
            # Normalize to UTC
            if ts.tzinfo is None:
                # Assume UTC if naive, or Local? Safer to assume UTC for YF History usually
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
                
            # Map to Tick
            return Tick(
                symbol=symbol,
                timestamp=ts.timestamp(), # Now guaranteed valid UTC timestamp
                bid=last_row["Close"], # YF doesn't give Bid/Ask easily in history
                ask=last_row["Close"],
                last=last_row["Close"],
                volume=int(last_row["Volume"]),
                source="YAHOO_FREE",
                sequence=int(time.time())
            )
        except Exception as e:
            logger.warning(f"Yahoo Fetch Failed for {symbol}: {e}")
            return None
