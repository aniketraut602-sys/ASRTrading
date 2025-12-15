from asr_trading.execution.execution_manager import BrokerAdapter, TradePlan
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
import asyncio

# wrapper for growwapi or unofficial api
try:
    # This is speculative as we don't have the lib installed yet, 
    # but we code to the standard pattern.
    from growwapi import GrowwAPI
    HAS_GROWW = True
except ImportError:
    HAS_GROWW = False

class GrowwAdapter(BrokerAdapter):
    def __init__(self):
        self.client = None
        self.connected = False
        
    def get_name(self) -> str:
        return "GROWW_INDIA"

    async def connect(self):
        if not HAS_GROWW:
            logger.error("GrowwAdapter: `growwapi` not installed. Please `pip install growwapi`.")
            return

        try:
            # Real Authentication
            api_key = cfg.GROWW_API_KEY
            api_secret = cfg.GROWW_API_SECRET
            
            if not api_key:
                logger.error("GrowwAdapter: Missing GROWW_API_KEY in Config.")
                self.connected = False
                return

            # Robust Init attempts
            try:
                # Attempt 1: Positional (Most common for wrappers)
                self.client = GrowwAPI(api_key)
            except TypeError:
                try:
                    # Attempt 2: access_token kwarg
                    self.client = GrowwAPI(access_token=api_key)
                except TypeError:
                     # Attempt 3: token kwarg
                     self.client = GrowwAPI(token=api_key)

            logger.info("GrowwAdapter: Connected successfully via API.")
            self.connected = True
            
        except Exception as e:
            logger.error(f"GrowwAdapter Connection Failed: {e}")
            # Reflection Debugging to find correct signature in logs
            try:
                import inspect
                sig = inspect.signature(GrowwAPI.__init__)
                logger.error(f"DEBUG: GrowwAPI Signature: {sig}")
            except:
                pass
            self.connected = False

    async def place_order(self, plan: TradePlan):
        if not self.connected:
            logger.error("GrowwAdapter: Not Connected. Cannot place order.")
            return {"status": "FAILED_CONNECTION"}

        logger.info(f"Groww: Placing REAL Order {plan.side} {plan.quantity} {plan.symbol}")
        
        try:
            # Map parameters to GrowwAPI expected format (Standardized)
            order_params = {
                "symbol": plan.symbol,
                "qty": plan.quantity,
                "type": "MARKET", # Default to Market for now
                "side": plan.side.upper(), # BUY/SELL
                "product": "MIS" # Intraday by default
            }
            
            # Execute Real Order
            res = self.client.place_order(order_params)
            logger.info(f"Groww: Order Submitted. Response: {res}")
            
            return {"order_id": res.get("order_id", "GROWW_UNKNOWN"), "status": "SUBMITTED", "response": res}
            
        except Exception as e:
            logger.error(f"Groww: Order Placement FAILED: {e}")
            return {"status": "FAILED_EXECUTION", "error": str(e)}
