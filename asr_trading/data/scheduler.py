from apscheduler.schedulers.background import BackgroundScheduler
from asr_trading.core.logger import logger
from asr_trading.data.ingestion import data_manager
import time

class DataScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.scheduler.add_job(self.fetch_market_data, 'interval', minutes=1, id='market_data_job')
            self.scheduler.start()
            self.is_running = True
            logger.info("Data Scheduler started.")

    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Data Scheduler stopped.")

    def fetch_market_data(self):
        """Job to fetch data for watched symbols"""
        from asr_trading.core.config import cfg
        from asr_trading.core.orchestrator import orchestrator
        import asyncio
        
        symbols = cfg.WATCHLIST
        logger.info(f"Scheduler: Triggering pipeline for {len(symbols)} symbols...")
        
        # We need to run async code from sync scheduler job
        # Ideally, scheduler should be async or use a worker pool.
        # For this prototype, we'll get the running loop or create a new one.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running (e.g. valid inside main.py), we create tasks
                for sym in symbols:
                    loop.create_task(orchestrator.run_cycle(sym))
            else:
                # Fallback for standalone testing
                loop.run_until_complete(self._run_batch(orchestrator, symbols))
        except RuntimeError:
             # Look for a new loop if none exists
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             loop.run_until_complete(self._run_batch(orchestrator, symbols))
             
    async def _run_batch(self, orchestrator, symbols):
        for sym in symbols:
            await orchestrator.run_cycle(sym)

scheduler_service = DataScheduler()
