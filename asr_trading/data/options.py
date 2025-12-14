import yfinance as yf
import pandas as pd
from datetime import datetime
from asr_trading.core.logger import logger
from asr_trading.analysis.greeks import greeks_engine

class OptionChainProvider:
    def __init__(self):
        pass

    def get_chain(self, symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                logger.warning(f"No options found for {symbol}")
                return pd.DataFrame()
            
            # Get nearest expiry
            nearest = expirations[0]
            chain = ticker.option_chain(nearest)
            calls = chain.calls
            puts = chain.puts
            
            # Enrich with Greeks
            # Basic assumptions: Risk-free rate 5%, Hist Volatility approximation
            # In a real engine, we'd fetch current Treasury Yield and Implied Vol
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            # Days to expiry
            expiry_date = datetime.strptime(nearest, "%Y-%m-%d")
            dte = (expiry_date - datetime.now()).days
            T = max(dte, 1) / 365.0
            
            # Calculate Greeks for Calls
            calls['greeks'] = calls.apply(lambda row: greeks_engine.calculate_greeks(
                S=current_price, K=row['strike'], T=T, r=0.05, sigma=row.get('impliedVolatility', 0.2), option_type="call"
            ), axis=1)
            
            return calls
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return pd.DataFrame()

options_provider = OptionChainProvider()
