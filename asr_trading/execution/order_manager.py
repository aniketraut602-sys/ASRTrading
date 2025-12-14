from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
from asr_trading.strategy.base import TradeSignal
import uuid
from datetime import datetime

class OrderManager:
    def __init__(self):
        self.positions = {} # symbol -> {entry, size, sl, tp, status, strategy}
        self.orders = []
        self.is_paper = cfg.IS_PAPER_TRADING

    def execute_signal(self, signal: TradeSignal, size: float = 1.0):
        if signal.action == "HOLD":
            return

        logger.info(f"Executing {signal.action} on {signal.symbol} (Confidence: {signal.confidence}%)")
        
        if self.is_paper:
            self._execute_paper(signal, size)
        else:
            logger.warning("Real execution not implemented yet. Falling back to paper.")
            self._execute_paper(signal, size)

    def _execute_paper(self, signal: TradeSignal, size: float):
        order_id = str(uuid.uuid4())[:8]
        order = {
            "id": order_id,
            "symbol": signal.symbol,
            "action": signal.action,
            "price": signal.entry_price,
            "size": size,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "time": datetime.utcnow(),
            "status": "FILLED"
        }
        self.orders.append(order)
        
        if signal.action == "BUY":
            self.positions[signal.symbol] = {
                "entry": signal.entry_price,
                "current_price": signal.entry_price,
                "size": size,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "strategy": signal.strategy_name,
                "status": "OPEN",
                "plan": "A"
            }
        elif signal.action == "SELL" and signal.symbol in self.positions:
            # Assume closing
            del self.positions[signal.symbol]
            
        logger.info(f"Paper Order {order_id} FILLED: {signal.action} {signal.symbol} @ {signal.entry_price}")

    def update_positions(self, market_data: dict):
        """Update current price of positions to check SL/TP"""
        for sym, pos in list(self.positions.items()):
            if sym in market_data:
                curr_price = market_data[sym]
                pos['current_price'] = curr_price
                
                # Check SL/TP (Simple checks)
                if curr_price <= pos['sl']:
                    logger.info(f"SL Hit for {sym}. Closing.")
                    self.close_position(sym, "SL Hit")
                elif curr_price >= pos['tp']:
                    logger.info(f"TP Hit for {sym}. Closing.")
                    self.close_position(sym, "TP Hit")

    def close_position(self, symbol: str, reason: str):
        if symbol in self.positions:
            logger.info(f"Closing position {symbol}. Reason: {reason}")
            del self.positions[symbol]

order_engine = OrderManager()
