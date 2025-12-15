import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Project Info
    PROJECT_NAME = "ASR Trading"
    VERSION = "1.0.0 (Enterprise)"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asr_trading.db")
    
    # API Keys (Real)
    KITE_API_KEY = os.getenv("KITE_API_KEY", "")
    KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    ALPACA_KEY_ID = os.getenv("ALPACA_KEY_ID", "")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # Telegram Bot
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")
    
    # Groww
    GROWW_API_KEY = os.getenv("GROWW_API_KEY", "")

    # Trading Rules (Enterprise Hardening)
    MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "70.0")) # Blueprint Requirement: >= 70%
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "5000.0")) # INR 5k Max Loss
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "50000.0")) # INR 50k Max Pos
    
    # Execution
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "PAPER") # PAPER, LIVE (Mock Removed)
    IS_PAPER = EXECUTION_MODE == "PAPER"
    IS_PAPER = EXECUTION_MODE == "PAPER"
    IS_PAPER_TRADING = IS_PAPER # Backward Compatibility Alias
    IS_LIVE = EXECUTION_MODE == "LIVE"
    
    # Execution Flow
    # AUTO: Bot decides and trades.
    # SEMI: Bot proposes, User approves via Telegram.
    EXECUTION_TYPE = os.getenv("EXECUTION_TYPE", "SEMI") # Default to Safe Mode
    
    # Risk
    MAX_OPEN_POSITIONS = 5
    RISK_PER_TRADE_PERCENT = 0.02 # 2% Rule

    # Watchlist
    # Watchlist (NSE Focus)
    WATCHLIST = ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "AAPL"] # Mixed for Demo

cfg = Config()
