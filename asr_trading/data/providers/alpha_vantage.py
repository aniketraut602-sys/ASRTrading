import aiohttp
import time
from typing import Optional
from asr_trading.data.feed_manager import FeedProvider
from asr_trading.data.canonical import Tick
from asr_trading.core.security import SecretsManager
from asr_trading.core.logger import logger

class AlphaVantageProvider(FeedProvider):
    def __init__(self):
        self.api_key = SecretsManager.get_secret("ALPHAVANTAGE_API_KEY", required=False)
        self.base_url = "https://www.alphavantage.co/query"
        self.session: Optional[aiohttp.ClientSession] = None

    def get_name(self) -> str:
        return "ALPHA_VANTAGE"

    async def connect(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        if not self.api_key:
             self.api_key = SecretsManager.get_secret("ALPHAVANTAGE_API_KEY", required=True)

        if not self.session:
            await self.connect()

        # Alpha Vantage GLOBAL_QUOTE
        url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.api_key}"
        
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"AV API Error: {resp.status}")
                    return None
                
                data = await resp.json()
                # { "Global Quote": { "01. symbol": "IBM", "05. price": "120.00", ... } }
                quote = data.get("Global Quote", {})
                if not quote:
                    if "Note" in data:
                        logger.warning(f"AV Rate Limit: {data['Note']}")
                    return None

                return Tick(
                    symbol=quote.get("01. symbol", symbol),
                    timestamp=time.time(), # AV doesn't give precise timestamp in quote, mostly EOD or delayed
                    bid=0.0,
                    ask=0.0,
                    last=float(quote.get("05. price", 0.0)),
                    volume=int(quote.get("06. volume", 0)),
                    source="ALPHA_VANTAGE",
                    sequence=int(time.time() * 1000)
                )
        except Exception as e:
            logger.error(f"AV Connection Error: {e}")
            raise e

    async def close(self):
        if self.session:
            await self.session.close()
