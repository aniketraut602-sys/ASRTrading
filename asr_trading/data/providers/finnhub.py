import aiohttp
import time
from typing import Optional
from asr_trading.data.feed_manager import FeedProvider
from asr_trading.data.canonical import Tick
from asr_trading.core.security import SecretsManager
from asr_trading.core.logger import logger

class FinnhubProvider(FeedProvider):
    def __init__(self):
        self.api_key = SecretsManager.get_secret("FINNHUB_API_KEY", required=False) # Not required for generic init, but needed for calls
        self.base_url = "https://finnhub.io/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    def get_name(self) -> str:
        return "FINNHUB"

    async def connect(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("FinnhubProvider: Session started.")

    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        if not self.api_key:
             # Try lazy load
             self.api_key = SecretsManager.get_secret("FINNHUB_API_KEY", required=True)

        if not self.session:
            await self.connect()

        url = f"{self.base_url}/quote?symbol={symbol}&token={self.api_key}"
        
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Finnhub API Error: {resp.status} - {await resp.text()}")
                    return None
                
                data = await resp.json()
                # Finnhub Quote: c: Current, d: Change, dp: %, h: High, l: Low, o: Open, pc: Prev Close, t: timestamp
                if 'c' not in data or data['c'] == 0:
                     return None

                return Tick(
                    symbol=symbol,
                    timestamp=data.get('t', time.time()), 
                    bid=data.get('l', 0.0), # Finnhub quote doesn't give B/A in free tier often, using Low as proxy or strictly 'c'
                    ask=data.get('h', 0.0), # Using High as proxy
                    last=float(data['c']),
                    volume=0, # Quote endpoint doesn't always have volume
                    source="FINNHUB",
                    sequence=int(time.time() * 1000) # Synthetic sequence
                )
        except Exception as e:
            logger.error(f"Finnhub Connection Error: {e}")
            raise e # Let CircuitBreaker handle it

    async def close(self):
        if self.session:
            await self.session.close()
