from typing import Any, Dict, List
from asr_trading.core.logger import logger
from asr_trading.core.avionics import telemetry

class InvariantViolation(Exception):
    pass

class Auditor:
    """
    Enforces Zero-Discrepancy Policy.
    "ASR Trading must never assume correctness — it must prove it."
    """
    
    @staticmethod
    def verify(condition: bool, error_msg: str, context: Dict[str, Any] = None):
        """
        Critical Invariant Check.
        If False, raises Alarm and throws Exception.
        """
        if not condition:
            full_msg = f"AUDIT FAILURE: {error_msg} | Context: {context}"
            logger.critical(full_msg)
            telemetry.record_event("audit_invariant_violation", {"error": error_msg, "context": context})
            raise InvariantViolation(full_msg)

    @staticmethod
    def audit_tick_integrity(tick: Any):
        """
        Verifies a Tick object is valid for processing.
        """
        Auditor.verify(tick is not None, "Tick is None")
        Auditor.verify(tick.last > 0, "Tick Price is Zero/Negative", {"symbol": getattr(tick, 'symbol', 'UNKNOWN')})
        Auditor.verify(tick.timestamp > 0, "Tick Timestamp is Invalid")

    @staticmethod
    def audit_plan_integrity(plan: Any):
        """
        Verifies a TradePlan before execution.
        """
        Auditor.verify(plan.quantity > 0, "Plan Quantity must be positive", {"id": plan.plan_id})
        Auditor.verify(plan.stop_loss < plan.limit_price if plan.side == "BUY" else plan.stop_loss > plan.limit_price, 
                       "Stop Loss Logic Error", {"side": plan.side, "limit": plan.limit_price, "sl": plan.stop_loss})
        Auditor.verify(plan.confidence > 0, "Plan Confidence Missing/Zero - Data Loss Detected", {"id": plan.plan_id})
        
    @staticmethod
    def reconcile_capital(internal_ledger: float, broker_balance: float):
        """
        Checks internal accounting vs broker reality.
        """
        diff = abs(internal_ledger - broker_balance)
        if diff > 1.0: # Tolerance $1
             Auditor.verify(False, f"Capital Mismatch > $1: Ledger={internal_ledger}, Broker={broker_balance}")

auditor = Auditor()
