import yfinance as yf
# import pandas as pd
# from alpha_vantage.timeseries import TimeSeries
# import finnhub
from asr_trading.core.config import cfg
from asr_trading.core.logger import logger
import pandas as pd

class DataProvider:
    """Abstract base class for data providers (implicit interface)"""
    def get_latest_price(self, symbol: str) -> float:
        raise NotImplementedError
    
    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        raise NotImplementedError

class YFinanceProvider(DataProvider):
    def get_latest_price(self, symbol: str) -> float:
        try:
            ticker = yf.Ticker(symbol)
            # Fast way to get latest price
            data = ticker.history(period="1d")
            if not data.empty:
                return data['Close'].iloc[-1]
            return 0.0
        except Exception as e:
            logger.error(f"YFinance Get Price Error for {symbol}: {e}")
            return 0.0

    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            return df
        except Exception as e:
            logger.error(f"YFinance History Error for {symbol}: {e}")
            return pd.DataFrame()

# TODO: Implement AlphaVantage and Finnhub wrappers properly when keys are available
# checks can be added to Config to see if keys are present before initializing these

class DataManager:
    def __init__(self):
        self.primary_provider = YFinanceProvider()
        # self.secondary_provider = AlphaVantageProvider() 
        logger.info("DataManager initialized with YFinance as primary")

    def get_price(self, symbol: str) -> float:
        return self.primary_provider.get_latest_price(symbol)
    
    def get_history(self, symbol: str, period: str="1mo", interval: str="1d") -> pd.DataFrame:
        return self.primary_provider.get_historical_data(symbol, period, interval)

data_manager = DataManager()
