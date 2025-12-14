import aiohttp
import time
from typing import Optional
from asr_trading.data.feed_manager import FeedProvider
from asr_trading.data.canonical import Tick
from asr_trading.core.security import SecretsManager
from asr_trading.core.logger import logger

class TwelveDataProvider(FeedProvider):
    def __init__(self):
        self.api_key = SecretsManager.get_secret("TWELVE_DATA_API_KEY", required=False)
        self.base_url = "https://api.twelvedata.com"
        self.session: Optional[aiohttp.ClientSession] = None

    def get_name(self) -> str:
        return "TWELVE_DATA"

    async def connect(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        if not self.api_key:
             self.api_key = SecretsManager.get_secret("TWELVE_DATA_API_KEY", required=True)

        if not self.session:
            await self.connect()

        # Twelve Data Real-Time Price
        url = f"{self.base_url}/price?symbol={symbol}&apikey={self.api_key}"
        
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"TwelveData API Error: {resp.status} - {await resp.text()}")
                    return None
                
                data = await resp.json()
                # {"price": "145.20"}
                if "price" not in data:
                     if "message" in data:
                         logger.warning(f"TwelveData Error: {data['message']}")
                     return None
                
                last_price = float(data["price"])

                return Tick(
                    symbol=symbol,
                    timestamp=time.time(), # API doesn't return TS in simple price EP
                    bid=0.0,
                    ask=0.0,
                    last=last_price,
                    volume=0, 
                    source="TWELVE_DATA",
                    sequence=int(time.time() * 1000)
                )
        except Exception as e:
            logger.error(f"TwelveData Connection Error: {e}")
            raise e

    async def close(self):
        if self.session:
            await self.session.close()
