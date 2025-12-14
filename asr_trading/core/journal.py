import os
import csv
import time
from typing import Dict, Any, Optional
from asr_trading.core.logger import logger

class TradeJournal:
    """
    Phase 18: System of Record.
    Logs every single trade outcome to a permanent CSV journal.
    This data feeds BrainStem (Learning) and Governance (Survivability).
    """
    def __init__(self, journal_path="data/journal.csv"):
        self.journal_path = journal_path
        self._ensure_journal_exists()

    def _ensure_journal_exists(self):
        if not os.path.exists(self.journal_path):
            try:
                os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
                with open(self.journal_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp", "strategy_id", "symbol", "side", 
                        "quantity", "entry_price", "exit_price", 
                        "pnl", "outcome", "confidence"
                    ])
            except Exception as e:
                logger.error(f"Journal: Failed to initialize journal at {self.journal_path}: {e}")

    def log_trade(self, trade_data: Dict[str, Any]):
        """
        Appends a completed trade record.
        Required keys: strategy_id, symbol, side, pnl, outcome (1=Win, 0=Loss)
        """
        try:
            with open(self.journal_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.time(),
                    trade_data.get("strategy_id", "UNKNOWN"),
                    trade_data.get("symbol", "UNKNOWN"),
                    trade_data.get("side", "UNKNOWN"),
                    trade_data.get("quantity", 0),
                    trade_data.get("entry_price", 0.0),
                    trade_data.get("exit_price", 0.0),
                    trade_data.get("pnl", 0.0),
                    trade_data.get("outcome", 0), # 1 or 0
                    trade_data.get("confidence", 0.0)
                ])
            logger.info(f"Journal: Logged trade for {trade_data.get('symbol')} (PnL: {trade_data.get('pnl')})")
        except Exception as e:
            logger.error(f"Journal: Failed to log trade: {e}")

# Singleton Instance
journal = TradeJournal()
