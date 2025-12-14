import asyncio
import signal
import sys
from asr_trading.core.config import cfg
from asr_trading.core.logger import logger

# Components
from asr_trading.data.feed_manager import feed_manager
from asr_trading.execution.execution_manager import execution_manager
from asr_trading.core.avionics import avionics_monitor

# Adapters
from asr_trading.execution.broker_adapters import KiteRealAdapter, AlpacaRealAdapter
from asr_trading.execution.groww_adapter import GrowwAdapter
from asr_trading.data.providers.polygon import PolygonProvider
from asr_trading.data.providers.yahoo import YahooFinanceProvider

# --- Graceful Shutdown ---
stop_event = asyncio.Event()

def handle_sigint(signum, frame):
    logger.info("Received SIGINT. Shutting down...")
    stop_event.set()

signal.signal(signal.SIGINT, handle_sigint)

async def main():
    logger.info(f"=== ASR Trading vNext Starting ===")
    logger.info(f"Mode: {cfg.EXECUTION_MODE}")
    
    # 1. Validation
    if cfg.IS_LIVE:
        logger.warning("!!! OPERATING IN LIVE MODE - REAL MONEY AT RISK !!!")
    elif cfg.IS_PAPER:
        logger.info("Operating in PAPER TRADING Mode.")
    else:
        logger.info("Operating in MOCK Mode.")

    # 2. Dependency Injection
    if cfg.IS_PAPER or cfg.IS_LIVE:
        # Load Real Adapters
        try:
            # Data Feeds
            if cfg.POLYGON_API_KEY:
                poly = PolygonProvider()
                feed_manager.register_provider("PRIMARY", poly)
                logger.info("Registered Polygon.io as PRIMARY feed.")
            else:
                logger.warning("Missing POLYGON_API_KEY. Trying Yahoo Finance (Free Tier).")
                yf_prov = YahooFinanceProvider()
                feed_manager.register_provider("PRIMARY", yf_prov)
                logger.info("Registered Yahoo Finance as PRIMARY feed (Fallback).")

            # Execution Brokers
            if cfg.GROWW_API_KEY:
                # Groww Adapter (User Specific)
                groww = GrowwAdapter()
                # Assuming Groww doesn't need async connect yet or it's handled internally
                execution_manager.set_brokers(primary=groww, secondary=None)
                logger.info("Registered Groww (India) as PRIMARY broker.")
            # Prefer Kite if configured (Indian)
            elif cfg.KITE_API_KEY:
                kite = KiteRealAdapter()
                execution_manager.set_brokers(primary=kite, secondary=None)
                logger.info("Registered Kite Zerodha as PRIMARY broker.")
            elif cfg.ALPACA_KEY_ID:
                alpaca = AlpacaRealAdapter()
                execution_manager.set_brokers(primary=alpaca, secondary=None)
                logger.info("Registered Alpaca as PRIMARY broker.")
            else:
                 logger.warning("Missing Broker Keys. Running in WATCH-ONLY Mode (Bot Active).")
                 # return # Don't exit, allow Bot to run
                 
        except Exception as e:
            logger.critical(f"Initialization Failed: {e}")
            return
            
    # Start Telegram Bot if Token present
    if cfg.TELEGRAM_TOKEN:
        logger.info("Initializing Telegram Bot...")
        from asr_trading.web.telegram_bot import telegram_bot
        # Start in background task
        asyncio.create_task(telegram_bot.start_bot())
    else:
        logger.info("MOCK Mode: Using Stub Adapters (Not implemented in this script). Exiting.")
        return

    # 3. Connection
    logger.info("Connecting to Data Feeds...")
    if feed_manager.primary:
        await feed_manager.primary.connect()

    # 4. Main Event Loop
    logger.info("System Ready. Waiting for Ticks...")
    
    # In a real system, we'd have a ticker loop or event consumer here.
    # For now, we simulate a Heartbeat loop.
    while not stop_event.is_set():
        avionics_monitor.heartbeat("main_loop")
        await asyncio.sleep(1)

    logger.info("System Shutdown Complete.")

if __name__ == "__main__":
    # if sys.platform == 'win32':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
