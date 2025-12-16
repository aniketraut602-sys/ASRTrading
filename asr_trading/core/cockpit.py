from datetime import datetime
import json
import threading
from typing import Dict, Any, List
from asr_trading.core.config import cfg

class CockpitState:
    """
    The Single Source of Truth for the Command Center UI.
    Thread-safe storage of all displayable system states.
    """
    def __init__(self):
        self._lock = threading.Lock()
        
        # Section A: System Status
        self.market_state = "UNKNOWN"
        self.data_feed_status = "DISCONNECTED"
        self.mode = cfg.EXECUTION_MODE
        self.exec_type = cfg.EXECUTION_TYPE
        self.telegram_status = "UNKNOWN"
        self.learning_active = True
        
        # Section B: Current Activity (The "Now")
        self.activity_status = "Initializing..."
        self.activity_detail = "System booting up."
        self.current_symbol = "N/A"
        self.current_strategy = "N/A"
        
        # Section D: Balance & Risk
        self.balance_available = 0.0
        self.margin_used = 0.0
        self.exposure = 0.0
        self.daily_risk_used = 0.0
        
        # Section E: Decisions
        self.last_decision = {
            "strategy": "None",
            "confidence": 0,
            "passed": [],
            "failed": [],
            "decision": "WAITING",
            "message": "No decisions yet."
        }
        
        # Extra Fields for API Contract
        self.last_rejected = {
            "instrument": "N/A",
            "reason": "None",
            "confidence": 0,
            "message": "No rejected trades yet"
        }
        
        self.monitored_setup = {
            "instrument": "N/A",
            "strategy": "None", 
            "confidence": 0,
            "message": "Not monitoring any specific setup"
        }
        
        # Section F: Messages/Logs
        self.messages: List[Dict] = []
        
    def update_rejected(self, instrument, reason, confidence, msg):
        with self._lock:
            self.last_rejected = {
                "instrument": instrument,
                "reason": reason,
                "confidence": confidence,
                "message": msg
            }

    def update_monitoring(self, instrument, strategy, confidence, msg):
        with self._lock:
            self.monitored_setup = {
                "instrument": instrument,
                "strategy": strategy,
                "confidence": confidence,
                "message": msg
            }
        
    def update_activity(self, status: str, detail: str = "", symbol: str = None, strategy: str = None):
        with self._lock:
            self.activity_status = status
            if detail: self.activity_detail = detail
            if symbol: self.current_symbol = symbol
            if strategy: self.current_strategy = strategy
    
    def update_market_state(self, state: str):
        with self._lock:
            self.market_state = state
            
    def update_feed_status(self, status: str):
        with self._lock:
            self.data_feed_status = status
            
    def update_balance(self, available: float, used: float, exposure: float):
        with self._lock:
            self.balance_available = available
            self.margin_used = used
            self.exposure = exposure
            
    def log_decision(self, decision: Dict):
        with self._lock:
            self.last_decision = decision
            
    def add_message(self, text: str, level: str = "INFO"):
        with self._lock:
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "text": text,
                "level": level
            }
            self.messages.append(entry)
            # Keep last 100 messages
            if len(self.messages) > 100:
                self.messages.pop(0)

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "system": {
                    "market": self.market_state,
                    "feed": self.data_feed_status,
                    "mode": self.mode,
                    "exec": self.exec_type,
                    "telegram": self.telegram_status,
                    "learning": "ACTIVE" if self.learning_active else "PAUSED"
                },
                "activity": {
                    "status": self.activity_status,
                    "detail": self.activity_detail,
                    "symbol": self.current_symbol,
                    "strategy": self.current_strategy
                },
                "finance": {
                    "balance": self.balance_available,
                    "margin": self.margin_used,
                    "exposure": self.exposure,
                    "risk_today": self.daily_risk_used
                },
                "decision": self.last_decision,
                "messages": self.messages[-20:] # Return last 20 for UI
            }

cockpit = CockpitState()
