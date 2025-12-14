from asr_trading.execution.execution_manager import BrokerAdapter
from asr_trading.strategy.planner import TradePlan
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg

# --- KITE ZERODHA ---
try:
    from kiteconnect import KiteConnect
    HAS_KITE = True
except ImportError:
    HAS_KITE = False

class KiteRealAdapter(BrokerAdapter):
    def __init__(self):
        if HAS_KITE:
            self.kite = KiteConnect(api_key=cfg.KITE_API_KEY)
            self.kite.set_access_token(cfg.KITE_ACCESS_TOKEN)
        else:
            self.kite = None
            logger.warning("KiteSDK missing. Real trading unavailable.")

    def get_name(self): return "KITE_REAL"

    async def place_order(self, plan: TradePlan):
        if not self.kite:
            raise Exception("KiteSDK not initialized.")

        # Map TradePlan to Kite Order Params
        variety = self.kite.VARIETY_REGULAR
        exchange = self.kite.EXCHANGE_NSE
        transaction_type = self.kite.TRANSACTION_TYPE_BUY if plan.side == "BUY" else self.kite.TRANSACTION_TYPE_SELL
        quantity = plan.quantity
        product = self.kite.PRODUCT_MIS
        order_type = self.kite.ORDER_TYPE_MARKET
        
        logger.info(f"KiteNet: Placing Order {plan.symbol} {plan.side} Qty={quantity}")
        
        try:
            order_id = self.kite.place_order(
                variety=variety,
                exchange=exchange,
                tradingsymbol=plan.symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type
            )
            return {"order_id": order_id, "status": "SUBMITTED"}
        except Exception as e:
            logger.error(f"Kite API Error: {e}")
            raise e

# --- ALPACA MARKETS ---
try:
    import alpaca_trade_api as tradeapi
    HAS_ALPACA = True
except ImportError:
    HAS_ALPACA = False

class AlpacaRealAdapter(BrokerAdapter):
    def __init__(self):
        if HAS_ALPACA:
            self.api = tradeapi.REST(
                cfg.ALPACA_KEY_ID,
                cfg.ALPACA_SECRET_KEY,
                base_url=cfg.ALPACA_BASE_URL
            )
        else:
            self.api = None
            logger.warning("AlpacaSDK missing.")

    def get_name(self): return "ALPACA_REAL"

    async def place_order(self, plan: TradePlan):
        if not self.api:
            raise Exception("AlpacaSDK not initialized.")
            
        side = "buy" if plan.side == "BUY" else "sell"
        logger.info(f"AlpacaNet: Placing Order {plan.symbol} {side} Qty={plan.quantity}")
        
        try:
            # Note: Alpaca API call is synchronous in this library usually, 
            # might need run_in_executor in real async loop.
            order = self.api.submit_order(
                symbol=plan.symbol,
                qty=plan.quantity,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            return {"order_id": order.id, "status": "SUBMITTED"}
        except Exception as e:
            logger.error(f"Alpaca API Error: {e}")
            raise e
