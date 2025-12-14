import pandas as pd
import numpy as np
import time
from typing import Dict, List, Optional, Any
from asr_trading.data.canonical import Tick, OHLC
from asr_trading.core.logger import logger
from asr_trading.core.avionics import telemetry

class FeatureException(Exception):
    pass

class WindowEngine:
    """
    Maintains sliding windows of OHLC data for multiple symbols.
    """
    def __init__(self, window_size=500):
        self.window_size = window_size
        self.buffers: Dict[str, List[OHLC]] = {} # symbol -> list of OHLC

    def add_ohlc(self, ohlc: OHLC):
        if ohlc.symbol not in self.buffers:
            self.buffers[ohlc.symbol] = []
        
        self.buffers[ohlc.symbol].append(ohlc)
        if len(self.buffers[ohlc.symbol]) > self.window_size:
            self.buffers[ohlc.symbol].pop(0)

    def get_dataframe(self, symbol: str) -> pd.DataFrame:
        if symbol not in self.buffers or not self.buffers[symbol]:
            return pd.DataFrame()
        
        data = [
            {
                "timestamp": x.timestamp,
                "open": x.open,
                "high": x.high,
                "low": x.low,
                "close": x.close,
                "volume": x.volume
            }
            for x in self.buffers[symbol]
        ]
        return pd.DataFrame(data)

class IndicatorLib:
    """
    Computes technical indicators on DataFrames.
    """
    @staticmethod
    def compute_all(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        try:
            # We use standard pandas operations to be dependency-lite if pandas-ta fails
            # SMA
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            
            # EMA
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # MACD
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
            # RSI (Hardened)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            
            # 17.1 Audit Fix: Div/0 protection
            loss = loss.replace(0, 0.0001) 
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['BB_Mid'] = df['close'].rolling(window=20).mean()
            df['BB_Std'] = df['close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
            df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
            
            # ATR (Approx)
            df['TR'] = np.maximum(
                (df['high'] - df['low']), 
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)), 
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['ATR'] = df['TR'].rolling(window=14).mean()
            
            # Volatility (Log returns std dev) (Hardened)
            # Avoid log(0)
            safe_close = df['close'].replace(0, np.nan).ffill() 
            df['Log_Ret'] = np.log(safe_close / safe_close.shift(1))
            df['Volatility'] = df['Log_Ret'].rolling(window=20).std()

            # 17.1 Audit Fix: Nan/Inf sanitization
            df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

            return df
        except Exception as e:
            logger.error(f"Indicator Computation Failed: {e}")
            telemetry.record_event("indicator_error", {"error": str(e)})
            return df

class FeatureEngine:
    """
    Orchestrator for feature generation.
    """
    def __init__(self):
        self.window_engine = WindowEngine()
        self.indicator_lib = IndicatorLib()

    def on_ohlc(self, ohlc: OHLC) -> Dict[str, Any]:
        """
        Ingests a new candle, updates window, computes features for the latest timestamp.
        """
        self.window_engine.add_ohlc(ohlc)
        df = self.window_engine.get_dataframe(ohlc.symbol)
        
        if len(df) < 50: # Warmup
            return {"status": "WARMUP"}

        df_features = self.indicator_lib.compute_all(df)
        
        # Extract latest row as feature vector
        latest = df_features.iloc[-1].to_dict()
        
        # Add 'Transforms' (Stub for FFT/Wavelet)
        # e.g., if we had numpy here we'd run fft on df['close'].values[-N:]
        latest['fft_dominant_period'] = 0.0 
        
        return {
            "symbol": ohlc.symbol,
            "timestamp": ohlc.timestamp,
            "features": latest,
            "status": "READY"
        }

feature_engine = FeatureEngine()
