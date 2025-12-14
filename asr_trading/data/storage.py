from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from asr_trading.core.config import cfg
from asr_trading.core.logger import logger

Base = declarative_base()

class TradeLog(Base):
    __tablename__ = 'trade_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20))
    action = Column(String(10)) # BUY, SELL
    quantity = Column(Float)
    price = Column(Float)
    strategy = Column(String(50))
    confidence_score = Column(Float)
    plan_used = Column(String(10)) # A, B, C, D, E
    status = Column(String(20)) # OPEN, CLOSED, FILLED, REJECTED
    notes = Column(Text)

class MarketData(Base):
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    timestamp = Column(DateTime)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    source = Column(String(20)) # YFINANCE, ALPHAVANTAGE, etc.

# Setup Database
try:
    engine = create_engine(cfg.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in cfg.DATABASE_URL else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {cfg.DATABASE_URL}")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise e

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
