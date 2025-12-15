from dataclasses import dataclass
from typing import Optional, Dict
from asr_trading.strategy.selector import StrategyProposal
from asr_trading.execution.risk_manager import risk_engine
from asr_trading.core.logger import logger
from asr_trading.core.auditor import Auditor

@dataclass
class TradePlan:
    plan_id: str
    symbol: str
    side: str
    quantity: int
    limit_price: float
    stop_loss: float
    take_profit: float
    plan_code: str # "A", "B"... "J"
    status: str # "PENDING", "EXECUTED", "REJECTED"
    confidence: float = 0.0 # 17.1 Audit Fix: Persist confidence

class PlannerEngine:
    """
    The State Machine.
    Converts a Strategy Proposal into a Concrete Execution Plan (Plans A-J).
    """
    def create_plan(self, proposal: StrategyProposal, current_price: float) -> Optional[TradePlan]:
        
        # 1. Consult Risk Manager
        # 18.3 Capital Preservation: Pass Volatility
        risk = risk_engine.check_trade(
            proposal.symbol, 
            current_price, 
            proposal.strategy_id, 
            proposal.confidence,
            volatility=proposal.volatility
        )
        
        if not risk["allowed"]:
            logger.warning(f"Planner: Strategy {proposal.strategy_id} REJECTED by Risk: {risk['reason']}")
            # In vNext, we might trigger Plan G (Auto-Reduce) if risk reason was 'Correlation'
            return None

        qty = risk["max_size"]
        
        # 2. Construct Plan Based on Code
        if proposal.plan_type == "A":
            # Normal Bracket Order
            # SL = 1% below, TP = 2% above (Simple Example)
            # In real system, Strategy should provide SL/TP or ATR based
            sl_pct = 0.01
            tp_pct = 0.02
            
            sl_price = current_price * (1 - sl_pct) if proposal.action == "BUY" else current_price * (1 + sl_pct)
            tp_price = current_price * (1 + tp_pct) if proposal.action == "BUY" else current_price * (1 - tp_pct)
            
            logger.info(f"Planner: Generated Plan A for {proposal.symbol} (Qty: {qty})")
            
            final_plan = TradePlan(
                plan_id=f"PLAN_{uuid.uuid4().hex[:8]}", # 17.1 Audit Fix: Collision proof
                symbol=proposal.symbol,
                side=proposal.action,
                quantity=qty,
                limit_price=current_price, # Market entry approximation
                stop_loss=sl_price,
                take_profit=tp_price,
                plan_code="A",
                status="PENDING",
                confidence=proposal.confidence
            )
            # 17.2 Zero-Discrepancy Check
            Auditor.audit_plan_integrity(final_plan)
            return final_plan
        
        # Handle other plans (B-J) stubs
        elif proposal.plan_type == "J":
            # Emergency Halt Plan
            logger.critical("Planner: Generating PLAN J (Emergency Halt)")
            return TradePlan(
                plan_id=f"PLAN_J_{int(time.time())}",
                symbol="ALL",
                side="HALT",
                quantity=0,
                limit_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                plan_code="J",
                status="EXECUTED" # Immediate effect
            )
        
        return None

import datetime
import uuid

planner_engine = PlannerEngine()
