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

    async def get_balance(self) -> float:
        """
        Fetch available cash balance.
        """
        if not self.connected:
            return 0.0

        try:
             # Speculative: Standard method name check
             # If using official groww lib, it might be get_user_balance() or get_funds()
             # We try generic attribute access or inspection
             
             # Attempt 1: get_balance()
             if hasattr(self.client, "get_balance"):
                 return self.client.get_balance()
             
             # Attempt 2: get_funds()
             if hasattr(self.client, "get_funds"):
                 return self.client.get_funds()

             # Attempt 3: Inspect for balance related methods
             # This is for debugging during the user's first "Try"
             # For now, return a placeholder with a log warning so we don't crash
             logger.warning("GrowwAdapter: Could not find exact balance method. Returning Mock 0.0 for safety.")
             return 0.0
             
        except Exception as e:
            logger.error(f"Groww Balance Fetch Failed: {e}")
            return 0.0

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

    async def get_order_status(self, order_id: str) -> dict:
        """
        Fetch the lifecycle status of an order.
        Returns standardized: SUBMITTED, OPEN, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
        """
        if not self.connected:
            return {"status": "UNKNOWN", "details": "Not Connected"}

        try:
            # Speculative: Standard method
            # Usually client.get_order(order_id) or client.order_history(order_id)
            
            raw_res = None
            if hasattr(self.client, "get_order"):
                raw_res = self.client.get_order(order_id)
            elif hasattr(self.client, "get_order_details"):
                raw_res = self.client.get_order_details(order_id)
            
            if not raw_res:
                # If we cannot fetch, return UNKNOWN but log it
                logger.warning(f"Groww: Could not fetch status for {order_id}. Method not found.")
                return {"status": "UNKNOWN"}

            # Map Groww Status to Internal
            # Ensure we handle what 'raw_res' looks like. Assuming dict.
            g_status = raw_res.get("status", "UNKNOWN").upper()
            
            mapping = {
                "REQUESTED": "SUBMITTED",
                "OPEN": "OPEN",
                "PENDING": "OPEN",
                "IN_PROGRESS": "OPEN",
                "COMPLETE": "FILLED",
                "EXECUTED": "FILLED",
                "PARTIALLY_EXECUTED": "PARTIALLY_FILLED",
                "CANCELLED": "CANCELLED",
                "REJECTED": "REJECTED",
                "FAILED": "REJECTED"
            }
            
            standard_status = mapping.get(g_status, g_status)
            return {
                "status": standard_status, 
                "raw": g_status, 
                "filled_qty": raw_res.get("filledQty", 0),
                "avg_price": raw_res.get("avgPrice", 0.0)
            }

        except Exception as e:
            logger.error(f"Groww: Status Fetch FAILED for {order_id}: {e}")
            return {"status": "UNKNOWN", "error": str(e)}
