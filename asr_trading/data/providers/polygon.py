from typing import Optional
from asr_trading.data.feed_manager import FeedProvider
from asr_trading.data.canonical import Tick
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
import time

# Try importing real SDK, fallback if not installed (for robustness)
try:
    from polygon import RESTClient, WebSocketClient
    from polygon.websocket.models import WebsiteMessage, WebSocketMessage
    HAS_SDK = True
except ImportError:
    HAS_SDK = False

class PolygonProvider(FeedProvider):
    def __init__(self):
        self.api_key = cfg.POLYGON_API_KEY
        self.client = None
        self.ws = None
        self.latest_ticks = {} # Symbol -> Tick

    def get_name(self) -> str:
        return "POLYGON_IO"

    async def connect(self):
        if not HAS_SDK:
            logger.error("PolygonSDK not installed. Please install 'polygon-api-client'.")
            return
            
        logger.info("PolygonProvider: Connecting WebSocket...")
        # Note: In a real async app, we'd use the async version or run in thread
        # This is a simplified wrapper adapting the SDK callback model to our polling `get_latest_tick` model
        # or we push updates to a queue.
        # For this design, we'll assume we have a REST fallback for "Snapshot" if WS not ready.
        
        self.client = RESTClient(self.api_key)
        
    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        if not HAS_SDK:
            return None

        # Prefer WebSocket cache if available (Low Latency)
        if symbol in self.latest_ticks:
            return self.latest_ticks[symbol]

        # Fallback to REST Snapshot (Higher Latency)
        try:
            # Snapshot API
            resp = self.client.get_snapshot_all(tickers=symbol)
            if resp and len(resp) > 0:
                s = resp[0]
                # Convert to Canonical Tick
                # Polygon uses: last_trade, min, day, etc.
                # Simplified mapping:
                tick = Tick(
                    symbol=symbol,
                    timestamp=time.time(),
                    bid=s.last_quote.bid_price if s.last_quote else 0.0,
                    ask=s.last_quote.ask_price if s.last_quote else 0.0,
                    last=s.last_trade.price if s.last_trade else 0.0,
                    volume=s.day.volume if s.day else 0,
                    source="POLYGON_REST",
                    sequence=int(time.time()*1000)
                )
                self.latest_ticks[symbol] = tick # Update cache
                return tick
        except Exception as e:
            logger.error(f"Polygon REST Failed: {e}")
            return None
        return None
