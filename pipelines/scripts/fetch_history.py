import yfinance as yf
import pandas as pd
import os
import time

# Configuration
DATA_DIR = "data/historical"
PERIOD = "5y" # User requested minimum 5 years
INTERVAL = "1d" # Daily bars are standard for long history training. 
                # (1h limit is usually 730 days on YF free)

# Universe Definition
# Mix of US Tech, Indices, and Indian Bluechips (NSE)
UNIVERSE = [
    # US Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD",
    
    # US Indices
    "SPY", "QQQ", "IWM", 
    
    # Forex / Macro
    "EURUSD=X", "GC=F", # Gold
    
    # Indian NSE (Suffix .NS)
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "NIFTYBEES.NS"
]

def fetch_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    print(f"=== Starting Data Harvest ===")
    print(f"Universe: {len(UNIVERSE)} symbols")
    print(f"Period: {PERIOD}, Interval: {INTERVAL}")
    
    success_count = 0
    
    for symbol in UNIVERSE:
        print(f"Fetching {symbol}...", end=" ", flush=True)
        try:
            # Add delay to respect free tier roughly
            time.sleep(0.5) 
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=PERIOD, interval=INTERVAL)
            
            if df.empty:
                print("EMPTY or FAILED.")
                continue
                
            # Clean up
            df.reset_index(inplace=True)
            
            # Save
            path = os.path.join(DATA_DIR, f"{symbol}.csv")
            df.to_csv(path, index=False)
            
            print(f"OK ({len(df)} rows)")
            success_count += 1
            
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"=== Harvest Complete ===")
    print(f"Success: {success_count}/{len(UNIVERSE)}")
    print(f"Data saved to: {os.path.abspath(DATA_DIR)}")

if __name__ == "__main__":
    fetch_data()
