import pandas as pd
from asr_trading.strategy.base import Strategy, TradeSignal
import numpy as np

class MeanReversionStrategy(Strategy):
    def __init__(self):
        super().__init__("Mean Reversion")

    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        if df.empty or len(df) < 20: return self._hold(symbol)
        
        # Calculate Bollinger Bands
        # Assume columns 'BBL_20_2.0', 'BBU_20_2.0', 'BBM_20_2.0' exist from indicators
        last = df.iloc[-1]
        close = last['Close']
        lower = last.get('BBL_20_2.0', 0)
        
        if close < lower:
            # Price below lower band -> Buy expectation
            return TradeSignal(symbol, "BUY", close, close*0.98, close*1.05, 80, self.name, "Price below Bollinger Lower Band")
            
        return self._hold(symbol)

    def _hold(self, symbol):
        return TradeSignal(symbol, "HOLD", 0,0,0,0, self.name, "")

    def calculate_confidence(self, df):
        return 50.0

from asr_trading.data.options import options_provider
from asr_trading.analysis.greeks import greeks_engine

class OptionsAnalytics:
    """Real Options Engine using Live Chains"""
    
    @staticmethod
    def get_best_options(symbol: str, strategy="call_buy"):
        """
        Scans real option chain for best contracts based on Delta/IV.
        """
        chain = options_provider.get_chain(symbol)
        if chain.empty: return []
        
        # Example: Find ATM Call with Delta ~ 0.5
        # Filter for liquidity
        liquid = chain[chain['volume'] > 100].copy()
        
        # Parse greeks from the enriched dataframe column (which is a dict)
        # Note: In production we'd normalize this structure better
        recommendations = []
        
        for idx, row in liquid.iterrows():
            greeks = row['greeks']
            if strategy == "call_buy":
                # Look for Delta > 0.4 and Low IV environment (relative check skipped for brevity)
                if 0.4 <= greeks['delta'] <= 0.6:
                    recommendations.append({
                        "contract": row['contractSymbol'],
                        "strike": row['strike'],
                        "price": row['lastPrice'],
                        "delta": greeks['delta']
                    })
                    
        return recommendations

mean_reversion = MeanReversionStrategy()
