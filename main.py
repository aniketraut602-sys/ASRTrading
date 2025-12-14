import sys
import asyncio
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
from asr_trading.data.scheduler import scheduler_service
from asr_trading.data.ingestion import data_manager
from asr_trading.strategy.scalping import scalping_strategy
from asr_trading.execution.order_manager import order_engine
from asr_trading.execution.risk_manager import risk_engine
from asr_trading.analysis.reliability import reliability_engine

async def main_loop():
    logger.info("ASR Trading Agent [MOONSHOT EDITION] Starting...")
    
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
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
