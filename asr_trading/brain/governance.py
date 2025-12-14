import json
import os
import numpy as np
from typing import Dict, List, Any
from asr_trading.core.logger import logger

class StrategyGovernance:
    """
    Phase 18.1 & 18.2: Long-Term Survivability.
    Tracks strategy health and enforces retirement for drifting components.
    """
    def __init__(self, stats_path="data/strategy_stats.json"):
        self.stats_path = stats_path
        self.stats: Dict[str, Dict] = {}
        self.load_stats()
        
        # Hard-coded Survivability Thresholds
        self.DRIFT_THRESHOLD = 0.40 # 40% Win Rate Warning
        self.RETIREMENT_THRESHOLD = 0.30 # 30% Win Rate Death
        self.MIN_TRADES_FOR_JUDGEMENT = 10 

    def load_stats(self):
        if os.path.exists(self.stats_path):
            try:
                with open(self.stats_path, 'r') as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.error(f"Governance: Failed to load stats: {e}")
                self.stats = {}

    def save_stats(self):
        try:
            os.makedirs(os.path.dirname(self.stats_path), exist_ok=True)
            with open(self.stats_path, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Governance: Failed to save stats: {e}")

    def update_trade(self, strategy_id: str, success: bool):
        """
        Records a trade outcome.
        """
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {
                "trades": 0,
                "wins": 0,
                "history": [], # Rolling window of last 50 (1=Win, 0=Loss)
                "status": "ACTIVE"
            }
        
        s = self.stats[strategy_id]
        
        if s["status"] == "RETIRED":
            logger.warning(f"Governance: Update received for RETIRED strategy {strategy_id}. Ignoring.")
            return

        s["trades"] += 1
        if success:
            s["wins"] += 1
            s["history"].append(1)
        else:
            s["history"].append(0)
            
        # Keep window collected
        if len(s["history"]) > 50:
            s["history"].pop(0)
            
        self._audit_strategy(strategy_id)
        self.save_stats()

    def _audit_strategy(self, strategy_id: str):
        """
        Checks for Drift or Failure.
        """
        s = self.stats[strategy_id]
        if len(s["history"]) < self.MIN_TRADES_FOR_JUDGEMENT:
            return # Too early to judge
            
        win_rate = sum(s["history"]) / len(s["history"])
        
        if win_rate < self.RETIREMENT_THRESHOLD:
            if s["status"] != "RETIRED":
                s["status"] = "RETIRED"
                logger.critical(f"GOVERNANCE ALERT: Strategy {strategy_id} RETIRED. Win Rate: {win_rate:.2f}")
        
        elif win_rate < self.DRIFT_THRESHOLD:
            if s["status"] != "DRIFTING":
                s["status"] = "DRIFTING"
                logger.warning(f"GOVERNANCE WARNING: Strategy {strategy_id} is DRIFTING. Win Rate: {win_rate:.2f}")
        
        else:
            # Recovery?
            if s["status"] == "DRIFTING":
                 s["status"] = "ACTIVE"
                 logger.info(f"Governance: Strategy {strategy_id} recovered to ACTIVE.")

    def is_allowed(self, strategy_id: str) -> bool:
        """
        Gatekeeper function.
        Returns False if Retired.
        """
        if strategy_id not in self.stats:
            return True # Innocent until proven guilty
            
        if self.stats[strategy_id]["status"] == "RETIRED":
            return False
            
        return True

governance = StrategyGovernance()
