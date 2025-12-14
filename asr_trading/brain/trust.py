import json
import os
from typing import List, Dict
from asr_trading.core.logger import logger

class TrustCalibrator:
    """
    Phase 18.8: Operator Trust Calibration.
    Adjusts system aggression based on how often the Human Operator approves proposals.
    """
    def __init__(self, data_path="data/trust_memory.json"):
        self.data_path = data_path
        self.history: List[int] = [] # 1 = Approved, 0 = Rejected
        self.WINDOW_SIZE = 20
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
            except Exception as e:
                logger.error(f"TrustCalibrator: Load failed: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w') as f:
                json.dump({"history": self.history}, f)
        except Exception as e:
            logger.error(f"TrustCalibrator: Save failed: {e}")

    def record_feedback(self, approved: bool):
        val = 1 if approved else 0
        self.history.append(val)
        if len(self.history) > self.WINDOW_SIZE:
            self.history.pop(0)
        self.save()
        
        score = self.get_trust_score()
        logger.info(f"Trust Update: New Score = {score:.2f} ({'Approved' if approved else 'Rejected'})")

    def get_trust_score(self) -> float:
        if not self.history:
            return 0.5 # Neutral start
        return sum(self.history) / len(self.history)

    def get_sizing_scalar(self) -> float:
        """
        Returns a multiplier for position sizing [0.1 - 1.2].
        """
        score = self.get_trust_score()
        
        if score >= 0.9: return 1.2  # Bonus aggression for high trust
        if score >= 0.7: return 1.0  # Normal
        if score >= 0.5: return 0.7  # Cautious
        if score >= 0.3: return 0.4  # Skeptical
        return 0.1                   # Probation (Minimal size)

trust_system = TrustCalibrator()
