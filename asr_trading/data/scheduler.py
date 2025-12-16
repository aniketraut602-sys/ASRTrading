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
            # Re-init if it was shutdown or fresh start
            if not self.scheduler.running:
                try:
                    self.scheduler.start()
                except Exception:
                    # If it was shutdown, we might need a fresh instance
                    self.scheduler = BackgroundScheduler()
                    self.scheduler.start()
            
            # Ensure job exists or add it
            if not self.scheduler.get_job('market_data_job'):
                self.scheduler.add_job(self.fetch_market_data, 'interval', minutes=1, id='market_data_job', replace_existing=True)
            else:
                 self.scheduler.resume_job('market_data_job')

            # 18.6 Continuous Learning Trigger (16:15 IST)
            if not self.scheduler.get_job('daily_review_job'):
                from asr_trading.analysis.daily_analyzer import daily_analyzer
                self.scheduler.add_job(daily_analyzer.perform_review, 'cron', hour=16, minute=15, id='daily_review_job', replace_existing=True)
                 
            self.is_running = True
            logger.info("Data Scheduler started/resumed.")

    def stop(self):
        if self.is_running:
            # Don't shutdown the thread, just pause the job to allow quick restart
            if self.scheduler.get_job('market_data_job'):
                self.scheduler.pause_job('market_data_job')
            self.is_running = False
            logger.info("Data Scheduler paused.")

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
                    task = loop.create_task(orchestrator.run_cycle(sym))
                    # Add callback to log exceptions if task fails
                    def handle_task_result(t):
                        try:
                            t.result()
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Scheduler: Task for {sym} failed: {e}", exc_info=True)
                    task.add_done_callback(handle_task_result)
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
