import sys
import asyncio
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
from asr_trading.data.scheduler import scheduler_service
from asr_trading.data.feed_manager import feed_manager
from asr_trading.data.providers.yahoo import YahooFinanceProvider
from asr_trading.data.providers.polygon import PolygonProvider
from asr_trading.strategy.scalping import scalping_strategy
from asr_trading.execution.order_manager import order_engine
from asr_trading.execution.risk_manager import risk_engine
from asr_trading.analysis.reliability import reliability_engine
from asr_trading.web.telegram_bot import telegram_bot

async def main_loop():
    logger.info("ASR Trading Agent [MOONSHOT EDITION] Starting...")
    
    # --- DATA FEED INITIALIZATION ---
    try:
        # 1. Primary Feed
        if cfg.POLYGON_API_KEY:
            logger.info("Initializing Polygon.io Feed...")
            poly = PolygonProvider()
            await poly.connect()
            feed_manager.register_provider("PRIMARY", poly)
        else:
            logger.warning("No Polygon Key. Using Yahoo Finance as PRIMARY.")
            yf_prov = YahooFinanceProvider()
            await yf_prov.connect()
            feed_manager.register_provider("PRIMARY", yf_prov)
            
    except Exception as e:
        logger.critical(f"Data Feed Init Failed: {e}")
        # We continue, but FeedManager will return None/Cache
    
    # --- BROKER INITIALIZATION ---
    from asr_trading.execution.execution_manager import execution_manager
    from asr_trading.execution.groww_adapter import GrowwAdapter
    from asr_trading.execution.broker_adapters import KiteRealAdapter, AlpacaRealAdapter
    
    if cfg.IS_PAPER or cfg.IS_LIVE:
        try:
            if cfg.GROWW_API_KEY:
                logger.info("Initializing Groww Adapter...")
                groww = GrowwAdapter()
                await groww.connect()
                if groww.connected:
                    execution_manager.set_brokers(primary=groww, secondary=None)
                    logger.info("[OK] Registered Groww (India) as PRIMARY broker.")
                else:
                    logger.warning("[X] Groww Connection Failed. Falling back...")
            
            elif cfg.KITE_API_KEY:
                execution_manager.set_brokers(primary=KiteRealAdapter(), secondary=None)
                logger.info("[OK] Registered Kite as PRIMARY broker.")
        except Exception as e:
            logger.error(f"Broker Init Failed: {e}")
            
    # Start Telegram Bot
    # NOTE: The Web Server (server.py) is the primary owner of the Telegram Bot.
    # If running CLI only, we can uncomment this, but usually we run server.py.
    logger.info("Bot startup deferred. Run 'python -m asr_trading.web.server' for full Bot/Web support.")

    # Start Scheduler
    scheduler_service.start()
    
    # Start Web Server in background task if needed, or run separately in Docker
    # In CLI mode, we just print the banner
    
    print("\n" + "="*50)
    print("ASR TRADING AGENT - ENTERPRISE COMMAND CENTER")
    print("Mode: " + cfg.EXECUTION_MODE)
    print("Serving Web UI at http://localhost:8000")
    print("Type /help for commands")
    print("="*50 + "\n")
    
    from asr_trading.brain.llm_client import llm_brain
    from asr_trading.data.async_ingestion import data_nexus
    
    running = True
    while running:
        try:
            cmd = await asyncio.to_thread(input, "ASR> ")
            cmd = cmd.strip().lower()
            
            if cmd == "/help":
                print("\nCommands:")
                print(" /analyze <txt> - Ask Offline AI for analysis")
                print(" /price <sym>   - Fetch Async Price (Multi-Provider)")
                print(" /signals       - Scan market")
                print(" /quit          - Exit")
                
            elif cmd.startswith("/analyze"):
                query = cmd.replace("/analyze", "").strip()
                if not query: query = "Explain the current market sentiment for Tech stocks."
                print(f" Thinking... (Sending to {llm_brain.model})")
                response = await asyncio.to_thread(llm_brain.analyze_market, query)
                print(f" AI Advice:\n{response}")

            elif cmd.startswith("/price"):
                sym = cmd.replace("/price", "").strip().upper()
                if not sym: sym = "AAPL"
                try:
                    price = await data_nexus.get_live_price(sym)
                    print(f" {sym}: ${price:.2f}")
                except Exception as e:
                    print(f" Error fetching price: {e}")

            elif cmd == "/signals":
                # Manual trigger for demo
                print("Scanning market...")
                syms = ["AAPL", "MSFT"] # Demo list
                found = False
                for s in syms:
                    df = data_manager.get_history(s)
                    sig = scalping_strategy.analyze(df, s)
                    if sig.action != "HOLD":
                        found = True
                        print(f" [SIGNAL] {sig.action} {s} | Conf: {sig.confidence}% | {sig.reason}")
                if not found:
                    print(" No strong signals found.")
            
            elif cmd == "/quit":
                print("Shutting down...")
                scheduler_service.stop()
                running = False
                
            else:
                print("Unknown command.")
                
        except EOFError:
            logger.warning("No Input detected (Daemon/Docker mode). Sleeping...")
            await asyncio.sleep(10)
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
