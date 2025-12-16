import json
import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from asr_trading.core.logger import logger

class BrainStem:
    """Scientific ML core for probability adjustment"""
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        self.is_trained = False
        # Updated to match features.py exact output
        # 17.5 Audit Fix: Feature alignment
        self.feature_columns = ['RSI', 'MACD', 'ATR', 'SMA_50', 'Volatility']
        
        # Auto-Load
        self.load_model()
        
    def train(self, historical_trades_df: pd.DataFrame):
        """
        Trains the model on past trade outcomes (Win/Loss).
        """
        if historical_trades_df.empty:
            logger.warning("No data to train BrainStem.")
            return

        # Mock feature extraction - In real system, these columns must be present in journal
        # 17.5 Fix: Validate columns exist
        missing = [c for c in self.feature_columns if c not in historical_trades_df.columns]
        if missing:
             logger.error(f"BrainStem Train: Missing columns in training data: {missing}")
             return

        X = historical_trades_df[self.feature_columns]
        y = historical_trades_df['outcome'] # 1 = Win, 0 = Loss
        
        # 17.5 Fix: Handle NaNs
        X = X.fillna(0)
        
        self.model.fit(X, y)
        self.is_trained = True
        logger.info("BrainStem trained successfully.")
        self.save_model() # Auto-save after training

    def predict_win_probability(self, features: dict) -> float:
        """
        Returns probability (0.0 - 1.0) of a win given current features.
        """
        if not self.is_trained:
            return 0.5 # Neutral
            
        df = pd.DataFrame([features])
        # Add missing columns with 0
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0.0

        # Reorder to match training
        df = df[self.feature_columns]
        
        try:
            prob = self.model.predict_proba(df)[0][1] # Probability of class 1 (Win)
            return prob
        except:
             return 0.5

    def save_model(self, path="model_registry/brain_model_v1.joblib"):
        import joblib
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.model, path)
        logger.info(f"BrainStem model saved to {path}")

    def load_model(self, path="model_registry/brain_model_v1.joblib"):
        import joblib
        if os.path.exists(path):
            try:
                self.model = joblib.load(path)
                self.is_trained = True
                logger.info(f"BrainStem model loaded from {path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
        else:
            logger.warning(f"No model found at {path}. BrainStem is untrained.")

class SelfStudy:
    def __init__(self):
        self.brain = BrainStem()
        # 18.6 Continuous Learning: Point to V2 Journal with Feature Snapshots
        self.journal_path = "data/journal_v2.csv"

    def nightly_review(self):
        """
        Runs analysis on today's logs and updates the brain.
        """
        logger.info("Running Nightly Self-Study...")
        
        if not os.path.exists(self.journal_path):
             logger.warning(f"SelfStudy: No journal found at {self.journal_path}. Skipping training.")
             return

        try:
            df = pd.read_csv(self.journal_path)
            # Filter for completed trades with defined outcome
            if 'outcome' not in df.columns:
                 logger.warning("SelfStudy: Journal missing 'outcome' column.")
                 return
            
            # Re-Train
            self.brain.train(df)
            logger.info(f"SelfStudy: Retrained BrainStem on {len(df)} records.")
            
        except Exception as e:
            logger.error(f"SelfStudy: Failed during nightly review: {e}")

cortex = SelfStudy()
