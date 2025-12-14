import pandas as pd
import pandas_ta as ta
from asr_trading.core.logger import logger

class Indicators:
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Adds all core indicators to the dataframe"""
        if df.empty:
            return df
        
        try:
            # RSI
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # MACD
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            
            # Bollinger Bands
            bb = ta.bbands(df['Close'], length=20)
            df = pd.concat([df, bb], axis=1)
            
            # ATR
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            # SMA / EMA
            df['SMA_50'] = ta.sma(df['Close'], length=50)
            df['EMA_20'] = ta.ema(df['Close'], length=20)
            
            # SuperTrend (pandas_ta usually returns 3 columns: SUPERT, SUPERTd, SUPERTl)
            st = ta.supertrend(df['High'], df['Low'], df['Close'], length=7, multiplier=3.0)
            df = pd.concat([df, st], axis=1)
            
            return df
        except Exception as e:
            logger.error(f"Error adding indicators: {e}")
            return df

    @staticmethod
    def get_rsi(df: pd.DataFrame, length=14):
        return ta.rsi(df['Close'], length=length)
