import pandas as pd
from asr_trading.strategy.base import Strategy, TradeSignal

class DeliveryStrategy(Strategy):
    """
    Delivery / Investing: Long-term hold.
    Focus: Fundamental valuation (PE Ratio) + Monthly Support levels.
    """
    def __init__(self):
        super().__init__("Delivery Investing")

    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        # In a real system, we would fetch Fundamental Data (Balance Sheet) here
        # Mocking fundamental check
        pe_ratio = 15.0 # Ideal: Fetch from DataNexus
        
        last = df.iloc[-1]
        close = last['Close']
        
        # Simple "Buy the Dip" logic on weekly timeframe 
        # (Assuming DF passed is high timeframe or we resample)
        
        if pe_ratio < 20:
             return TradeSignal(
                symbol=symbol,
                action="BUY",
                price=close,
                stop_loss=close * 0.80, # Very wide SL
                take_profit=close * 2.0, # 100% return target
                confidence=80.0, 
                strategy=self.name,
                reason="Value Buy (Low PE)"
            )
            
        return self._hold(symbol)

    def _hold(self, symbol):
        return TradeSignal(symbol, "HOLD", 0,0,0,0, self.name, "")

    def calculate_confidence(self, df):
        return 80.0

delivery_strategy = DeliveryStrategy()
