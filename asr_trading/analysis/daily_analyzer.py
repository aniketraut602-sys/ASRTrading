import pandas as pd
import os
import time
from asr_trading.core.logger import logger
from asr_trading.brain.learning import cortex
from asr_trading.core.journal import journal

class DailyAnalyzer:
    """
    Phase 18: Continuous Learning System.
    Performed at Market Close (16:00) or on demand.
    1. Retrains BrainStem on latest Journal data.
    2. Calculates daily performance metrics.
    3. Notifies Operator.
    """
    def __init__(self):
        self.journal_path = journal.journal_path
        
    def perform_review(self):
        logger.info("DailyAnalyzer: Starting Market Close Review...")
        
        if not os.path.exists(self.journal_path):
            logger.warning("DailyAnalyzer: No journal found. Nothing to analyze.")
            return "No Journal Data"
            
        try:
            # 1. Retrain BrainStem
            # SelfStudy.nightly_review handles reading and training
            cortex.nightly_review()
            
            # 2. Performance Analysis
            df = pd.read_csv(self.journal_path)
            if df.empty:
                return "Journal Empty"
                
            # Filter for TODAY (Optional, for now analyze all-time or last 24h?)
            # Let's do All-Time stats + Today specific
            
            # Simple Stats
            total_trades = len(df)
            wins = len(df[df['outcome'] == 1])
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = df['pnl'].sum()
            
            summary = (
                f"DAILY REVIEW COMPLETE\n"
                f"---------------------\n"
                f"Trades logged: {total_trades}\n"
                f"Win Rate: {win_rate:.1f}%\n"
                f"Net PnL: ₹{total_pnl:.2f}\n"
                f"BrainStem: Retrained & Updated."
            )
            
            logger.info(summary)
            
            # 3. Notify via Telegram (if available)
            self._notify_bot(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"DailyAnalyzer: Review Failed: {e}", exc_info=True)
            return f"Review Failed: {e}"

    def _notify_bot(self, message):
         try:
             # Avoid Circular Import at top level
             from asr_trading.web.telegram_bot import telegram_bot
             import asyncio
             
             if telegram_bot.running:
                 # We need to run this async
                 loop = asyncio.get_event_loop()
                 if loop.is_running():
                      loop.create_task(telegram_bot.send_message(message))
                 else:
                      # If called from sync scheduler context without loop (unlikely via generic handler)
                      pass 
         except Exception:
             pass 

daily_analyzer = DailyAnalyzer()
