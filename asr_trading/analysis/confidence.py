import pandas as pd
from asr_trading.core.config import cfg

class ConfidenceCalculator:
    def __init__(self):
        pass

    def calculate(self, df: pd.DataFrame, signal_type: str) -> float:
        """
        Calculates confidence score based on confluence of indicators.
        signal_type: 'BUY' or 'SELL'
        """
        if df.empty:
            return 0.0
        
        score = 0
        latest = df.iloc[-1]
        
        # 1. RSI Confluence (Weight: 20%)
        rsi = latest.get('RSI', 50)
        if signal_type == 'BUY':
            if 30 <= rsi <= 50: score += 15
            elif rsi < 30: score += 20 # Oversold
        elif signal_type == 'SELL':
            if 50 <= rsi <= 70: score += 15
            elif rsi > 70: score += 20 # Overbought

        # 2. MACD Confluence (Weight: 20%)
        macd = latest.get('MACD', 0)
        signal = latest.get('MACD_Signal', 0)
        if signal_type == 'BUY' and macd > signal: score += 20
        if signal_type == 'SELL' and macd < signal: score += 20
        
        # 3. SuperTrend Confluence (Weight: 25%)
        # Assuming SuperTrend returns trend direction (1 for up, -1 for down) in column 'SUPERTd_7_3.0'
        st_dir = latest.get('SUPERTd_7_3.0', 0)
        if signal_type == 'BUY' and st_dir == 1: score += 25
        if signal_type == 'SELL' and st_dir == -1: score += 25
        
        # 4. Pattern Confluence (Weight: 15%)
        # TODO: Check candlestick patterns columns if implemented
        if signal_type == 'BUY' and latest.get('Pattern_BullishEngulfing', False): score += 15
        
        # 5. Volume/Trend Alignment (Weight: 20%)
        # Simple check: Price > SMA_50 for BUY
        sma_50 = latest.get('SMA_50', 0)
        if sma_50 > 0:
            if signal_type == 'BUY' and latest['Close'] > sma_50: score += 20
            if signal_type == 'SELL' and latest['Close'] < sma_50: score += 20
            
        return min(100.0, score)

confidence_engine = ConfidenceCalculator()
