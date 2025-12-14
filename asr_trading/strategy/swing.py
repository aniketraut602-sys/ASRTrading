import pandas as pd
from asr_trading.strategy.base import Strategy, TradeSignal

class SwingStrategy(Strategy):
    """
    Swing Trading: Holds positions for days/weeks.
    Focus: Higher Timeframe Trends (Daily/Weekly), MA Crossovers.
    """
    def __init__(self):
        super().__init__("Swing Trader")

    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        if df.empty or len(df) < 50: return self._hold(symbol)
        
        # Logic: 20 SMA > 50 SMA (Golden Cross) + RSI < 70 (Not overbought)
        # Assuming indicators are pre-calculated in DF
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        sma20 = last.get('SMA_20', 0)
        sma50 = last.get('SMA_50', 0)
        rsi = last.get('RSI_14', 50)
        
        # Trend check
        if sma20 > sma50 and rsi < 70:
            # Check for recent crossover (within last 3 candles)
            # Simplified for MVP
            return TradeSignal(
                symbol=symbol,
                action="BUY",
                price=last['Close'],
                stop_loss=last['Close'] * 0.95, # Wider SL for swing
                take_profit=last['Close'] * 1.15, # Larger target
                confidence=75.0, # Base confidence
                strategy=self.name,
                reason="SMA 20/50 Bullish Trend"
            )
            
        return self._hold(symbol)

    def _hold(self, symbol):
        return TradeSignal(symbol, "HOLD", 0,0,0,0, self.name, "")

    def calculate_confidence(self, df):
        return 75.0 # Placeholder

swing_strategy = SwingStrategy()
