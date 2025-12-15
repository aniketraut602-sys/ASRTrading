from dataclasses import dataclass
from typing import Dict, Optional, Any
from asr_trading.core.logger import logger
from asr_trading.core.avionics import telemetry
from asr_trading.brain.trust import trust_system
from asr_trading.core.config import cfg

@dataclass
class RiskProfile:
    max_capital_per_trade_pct: float = cfg.RISK_PER_TRADE_PERCENT
    max_daily_loss_pct: float = 0.03        # 3% max daily drawdown 
    max_open_trades: int = cfg.MAX_OPEN_POSITIONS
    min_liquidity_volume: int = 100000

class RiskManager:
    """
    The Gatekeeper.
    Validates every strategy proposal against hard constraints.
    """
    def __init__(self):
        self.profile = RiskProfile()
        self.current_daily_loss = 0.0
        self.open_trades_count = 0
        # 19.2 Removal of Mock Capital
        # Default to 100,000 INR for Paper/Dev if not specified
        # In LIVE mode, this should be updated via sync_balance()
        self.total_capital = 100000.0 

    def get_lot_size(self, symbol: str) -> int:
        """
        Returns the fixed lot size for indices, or 1 for stocks.
        """
        sym = symbol.upper()
        if "NIFTY" in sym and "BANK" not in sym: return 75
        if "BANKNIFTY" in sym: return 15
        if "FINNIFTY" in sym: return 40
        return 1

    def check_trade(self, symbol: str, price: float, strategy_id: str, confidence: float, volatility: float = 0.0) -> Dict[str, Any]:
        """
        Returns {"allowed": bool, "reason": str, "max_size": int}
        """
        # 1. Daily Loss Circuit Breaker
        if self.current_daily_loss >= (self.total_capital * self.profile.max_daily_loss_pct):
            return {"allowed": False, "reason": "Daily Loss Limit Exceeded", "max_size": 0}

        # 2. Max Open Trades
        if self.open_trades_count >= self.profile.max_open_trades:
            return {"allowed": False, "reason": "Max Open Trades Reached", "max_size": 0}

        # 3. Calculate Safe Size
        # Simple Logic: Risk 2% of capital
        risk_amt = self.total_capital * self.profile.max_capital_per_trade_pct
        # Assuming no leverage for calculation base
        max_qty = int(risk_amt / price)
        
        if max_qty <= 0:
             return {"allowed": False, "reason": "Capital insufficient for 1 lot", "max_size": 0}

        # 12.1 Options Lot Logic (Fixed Sizes)
        # If the symbol has a defined lot size (e.g. NIFTY=75), we enforce multiples or single lots
        fixed_lot = self.get_lot_size(symbol)
        if fixed_lot > 1:
            # For Options/Indices, we usually start with 1 Lot in risk-managed mode
            # Check if capital allows at least 1 lot
            cost_1_lot = fixed_lot * price
            if risk_amt < cost_1_lot:
                 # If 2% risk is less than cost of 1 lot, we might block OR allow 1 lot if within global max loss
                 # Here, we strictly block to fit risk profile
                 return {"allowed": False, "reason": f"Risk ({risk_amt}) < Cost of 1 Lot ({cost_1_lot})", "max_size": 0}
            
            # Default to 1 Lot for "First Version" of Options Logic
            max_qty = fixed_lot
            logger.info(f"RiskManager: Enforcing Fixed Lot Size for {symbol}: {max_qty}")

        # 18.3 Capital Preservation: Logic
        # A. Soft Drawdown Brake
        daily_limit = self.total_capital * self.profile.max_daily_loss_pct
        if self.current_daily_loss > (daily_limit * 0.5):
            logger.warning("Risk: Soft Drawdown Brake Engaged (Size reduced 50%)")
            max_qty = max(1, int(max_qty * 0.5))

        # B. Volatility Scaling (Survival Mode)
        # If volatility is high, we reduce size to avoid ruin sequences
        if volatility > 0.005: # High vol threshold (adjustable)
             scalar = 0.005 / volatility
             original_qty = max_qty
             max_qty = max(1, int(max_qty * scalar))
             if max_qty < original_qty:
                 logger.info(f"Risk: Volatility Scaling engaged. Size {original_qty} -> {max_qty} (Vol={volatility:.4f})")

        # 18.8 Trust Calibration
        trust_scalar = trust_system.get_sizing_scalar()
        if trust_scalar != 1.0:
            max_qty = max(1, int(max_qty * trust_scalar))
            if trust_scalar < 1.0:
                logger.info(f"Risk: Trust Calibration reduced size (Scalar={trust_scalar})")

        # 4. Confidence Gate (Simple)
        if confidence < 0.6:
             return {"allowed": False, "reason": "Confidence too low for Risk Profile", "max_size": 0}

        return {
            "allowed": True,
            "reason": "OK",
            "max_size": max_qty
        }

    def record_loss(self, amount: float):
        self.current_daily_loss += amount
        if self.current_daily_loss >= (self.total_capital * self.profile.max_daily_loss_pct):
            logger.critical("RISK MANAGER: DAILY LOSS LIMIT HIT! HALTING TRADING.")
            telemetry.record_event("risk_halt_daily_loss", {"loss": self.current_daily_loss})

risk_engine = RiskManager()
