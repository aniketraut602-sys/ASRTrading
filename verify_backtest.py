import asyncio
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
# Setup Logger
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("ASR_Backtest")

from asr_trading.strategy.scalping import scalping_strategy

class RealBacktester:
    def __init__(self, symbol="TCS.NS", period="1mo", interval="1h"):
        self.symbol = symbol
        self.period = period
        self.interval = interval
        self.history = []

    def fetch_data(self):
        logger.info(f"Fetching real data for {self.symbol}...")
        df = yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)
        if df.empty:
            logger.error("No data fetched.")
            return pd.DataFrame()
        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def run(self):
        df = self.fetch_data()
        if df.empty: return

        logger.info(f"Running Real Logic Backtest on {len(df)} candles...")
        
        # Simulate rolling window
        window_size = 50
        if len(df) < window_size:
            logger.error("Not enough data.")
            return

        for i in range(window_size, len(df)):
            # Slice window (Past 50 candles up to i)
            window = df.iloc[i-window_size:i+1].copy()
            current_candle = window.iloc[-1]
            current_date = current_candle.name
            
            # --- THE TRUTH CHECK ---
            # We are calling the ACTUAL strategy file.
            signal = scalping_strategy.analyze(window, self.symbol)
            
            if signal.action != "HOLD":
                self.history.append({
                    "Date": str(current_date),
                    "Action": signal.action,
                    "Price": float(current_candle['Close']),
                    "Confidence": signal.confidence,
                    "Reason": signal.reason
                })
                logger.info(f"⚡ SIGNAL: {current_date}: {signal.action} @ {current_candle['Close']:.2f} | {signal.reason}")

        self.print_summary()

    def print_summary(self):
        print("\n" + "="*40)
        print(f"   BACKTEST RESULTS: {self.symbol}")
        print("="*40)
        if not self.history:
            print("No signals generated with current logic (RSI<40 + MACD X).")
            print("Try a different symbol or timeframe.")
        else:
            print(f"Total Signals: {len(self.history)}")
            for t in self.history:
                print(f"[{t['Action']}] {t['Date']} @ {t['Price']} | {t['Reason']}")

if __name__ == "__main__":
    # Test on Nifty (Index) to prove options mapping logic potential
    bt = RealBacktester(symbol="^NSEI", period="1y", interval="1d") # Nifty 50
    bt.run()
