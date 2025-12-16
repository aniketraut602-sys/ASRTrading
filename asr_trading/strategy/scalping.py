import pandas as pd
from asr_trading.strategy.base import Strategy, TradeSignal
from asr_trading.analysis.indicators import Indicators
from asr_trading.analysis.confidence import confidence_engine
from asr_trading.analysis.patterns import pattern_detector

class ScalpingStrategy(Strategy):
    def __init__(self):
        super().__init__("Scalping")

    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        if df.empty or len(df) < 50:
             return TradeSignal(symbol, "HOLD", 0, 0, 0, 0, self.name, "Insufficient Data")

        # Ensure indicators are present
        df = Indicators.add_all_indicators(df)
        
        # Patterns (returns list, just attaching for side effect or logging if needed)
        # Scalping strategy might not use patterns directly in this version, or we adapt logic.
        # For now, just run detection to ensure no crash.
        patterns = pattern_detector.analyze(df, symbol)
        
        last = df.iloc[-1]
        
        # Logic: RSI Oversold + MACD Crossover -> BUY
        signal = "HOLD"
        reason = ""
        
        rsi = last.get('RSI', 50)
        macd = last.get('MACD', 0)
        macd_signal = last.get('MACD_Signal', 0)
        
        # Buy Condition
        if rsi < 40 and macd > macd_signal:
            signal = "BUY"
            reason = "RSI Oversold + MACD Bullish"
        
        # Sell Condition
        elif rsi > 60 and macd < macd_signal:
            signal = "SELL"
            reason = "RSI Overbought + MACD Bearish"
            
        if signal == "HOLD":
            return TradeSignal(symbol, "HOLD", 0, 0, 0, 0, self.name, "No Signal")

        # Calculate Confidence
        confidence = self.calculate_confidence(df, signal)
        
        # Set Entry/SL/TP
        price = last['Close']
        stop_loss = price * 0.99 if signal == "BUY" else price * 1.01
        take_profit = price * 1.02 if signal == "BUY" else price * 0.98
        
        return TradeSignal(symbol, signal, price, stop_loss, take_profit, confidence, self.name, reason)

    def calculate_confidence(self, df: pd.DataFrame, signal_type: str = "BUY") -> float:
        return confidence_engine.calculate(df, signal_type)

scalping_strategy = ScalpingStrategy()
