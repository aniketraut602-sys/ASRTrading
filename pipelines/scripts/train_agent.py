import pandas as pd
import glob
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from asr_trading.brain.learning import cortex
from asr_trading.analysis.indicators import Indicators
from asr_trading.core.logger import logger

DATA_DIR = "data/historical"
MODEL_PATH = "model_registry/brain_model_v1.joblib"

def train_agent():
    logger.info("=== Starting Agent Training ===")
    
    # 1. Load Data
    files = glob.glob(f"{DATA_DIR}/*.csv")
    if not files:
        logger.error("No historical data found. Run 'python scripts/fetch_history.py' first.")
        return

    logger.info(f"Found {len(files)} historical files.")
    
    master_df = pd.DataFrame()
    
    for f in files:
        try:
            df = pd.read_csv(f)
            if df.empty: continue
            
            # 2. Tech Analysis (Feature Engineering)
            # Use official Indicators class to ensure parity with Live Engine
            df = Indicators.add_all_indicators(df)
            
            # 3. Create Target (Auto-Labeling)
            df['future_close'] = df['Close'].shift(-1)
            df['outcome'] = (df['future_close'] > df['Close']).astype(int)
            
            # Filter to required columns ONLY before dropping NaNs
            # BrainStem uses: RSI, MACDh_12_26_9, ATR, SMA_50
            req_cols = cortex.brain.feature_columns + ['outcome']
            
            # Check if columns exist (pandas_ta might have failed silently or names differ)
            missing = [c for c in req_cols if c not in df.columns]
            if missing:
                logger.warning(f"Missing columns in {f}: {missing}")
                continue

            df = df[req_cols]
            
            # Fill NaNs from indicators
            before_drop = len(df)
            df.dropna(inplace=True)
            after_drop = len(df)
            
            print(f"Processed {os.path.basename(f)}: {before_drop} -> {after_drop} rows.")
            
            if not df.empty:
                master_df = pd.concat([master_df, df])
                
                
        except Exception as e:
            logger.warning(f"Failed to process {f}: {e}")
            print(f"ERROR processing {f}: {e}") # Debug to stdout

    if master_df.empty:
        logger.error("Master DataFrame is empty. Training aborted.")
        print("Master DataFrame is empty. Check logs.")
        return

    logger.info(f"Training on {len(master_df)} rows of data...")
    
    # 4. Train
    # BrainStem expects 'outcome' column and looks for self.feature_columns
    try:
        cortex.brain.train(master_df)
        
        # 5. Save
        if not os.path.exists("model_registry"):
            os.makedirs("model_registry")
            
        cortex.brain.save_model(MODEL_PATH)
        logger.info(f"Training Complete. Model saved to {MODEL_PATH}")
        
    except Exception as e:
        logger.error(f"Training Failed: {e}")

if __name__ == "__main__":
    train_agent()
