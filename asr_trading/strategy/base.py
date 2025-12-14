from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass

@dataclass
class TradeSignal:
    symbol: str
    action: str # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy_name: str
    reason: str

class Strategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        """Analyzes data and returns a signal"""
        pass
    
    @abstractmethod
    def calculate_confidence(self, df: pd.DataFrame) -> float:
        """Returns confidence score 0-100"""
        pass
