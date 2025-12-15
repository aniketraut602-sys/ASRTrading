import pandas as pd
import numpy as np
from asr_trading.core.logger import logger

class Indicators:
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Adds all core indicators to the dataframe using pure Pandas (No External Depts)"""
        if df.empty:
            return df
        
        try:
            # --- RSI (14) ---
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            df['RSI'] = df['RSI'].fillna(50) # Fallback

            # --- MACD (12, 26, 9) ---
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_s'] = df['MACD'].ewm(span=9, adjust=False).mean() # Signal Line
            
            # --- Bollinger Bands (20, 2) ---
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            df['BBL_20_2.0'] = df['SMA_20'] - (df['STD_20'] * 2) # Lower
            df['BBM_20_2.0'] = df['SMA_20']                      # Mid
            df['BBU_20_2.0'] = df['SMA_20'] + (df['STD_20'] * 2) # Upper
            
            # --- ATR (14) ---
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(14).mean()
            
            # --- SMA / EMA ---
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            
            return df
        except Exception as e:
            logger.error(f"Error adding indicators: {e}")
            return df

    @staticmethod
    def get_rsi(df: pd.DataFrame, length=14):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
