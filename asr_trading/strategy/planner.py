from dataclasses import dataclass
from typing import Optional, Dict
from asr_trading.strategy.selector import StrategyProposal
from asr_trading.execution.risk_manager import risk_engine
from asr_trading.core.logger import logger
from asr_trading.core.auditor import Auditor
import time

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
    entry_price: float = 0.0 # Execution price or estimated entry
    confidence: float = 0.0 # 17.1 Audit Fix: Persist confidence
    rejection_reason: Optional[str] = None # Why it was blocked
    features: Optional[Dict] = None # 18.6 Feature Snapshot for Learning

    @property
    def risk_reward_ratio(self) -> float:
        if self.stop_loss == 0.0 or self.take_profit == 0.0 or self.limit_price == 0.0:
            return 0.0
        
        risk = abs(self.limit_price - self.stop_loss)
        reward = abs(self.take_profit - self.limit_price)
        
        if risk == 0: return 0.0
        return round(reward / risk, 2)


class PlannerEngine:
    """
    The State Machine.
    Converts a Strategy Proposal into a Concrete Execution Plan (Plans A-J).
    """
    
    def generate_proposal(self, strategy_id: str, symbol: str, action: str, confidence: float, current_price: float) -> Optional['TradePlan']:
        """
        Generates a PROPOSED TradePlan without executing it.
        This allows the UI to show the user exactly what will happen.
        """
        # Create a mock proposal
        proposal = StrategyProposal(
            strategy_id=strategy_id,
            symbol=symbol,
            action=action,
            confidence=confidence,
            rationale="Manual Execution Proposal",
            plan_type="A", # Default to Plan A for manual
            volatility=0.0 # Will be fetched if needed
        )
        
        # Reuse CREATE logic but set status to PROPOSED
        plan = self.create_plan(proposal, current_price)
        if plan:
            # Fix: Do not overwrite REJECTED status
            if plan.status != "REJECTED":
                plan.status = "PROPOSED"
            return plan
        return None

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
            # Return a REJECTED plan so UI/Bot knows why
            return TradePlan(
                plan_id=f"REJECT_{int(time.time())}",
                symbol=proposal.symbol,
                side=proposal.action,
                quantity=0,
                limit_price=current_price,
                stop_loss=0.0,
                take_profit=0.0,
                plan_code="REJECTED",
                status="REJECTED",
                confidence=proposal.confidence,
                rejection_reason=risk['reason']
            )

        qty = risk["max_size"]
        
        # 2. Construct Plan Based on Code
        if proposal.plan_type == "A":
            # Normal Bracket Order
            # SL = 1% below, TP = 2% above (Simple Example)
            # In real system, Strategy should provide SL/TP or ATR based
            # 51. Determine Instrument (Spot vs Option)
            from asr_trading.execution.options_mapper import options_mapper
            tradin_sym = proposal.symbol
            
            # Auto-Map to Option if Index
            if "NIFTY" in proposal.symbol:
                # Interpret Signal: BUY = CE, SELL = PE
                # Scalping Strategy "SELL" usually means Short Signal. We map to Long Put.
                option_side = "BUY" # We always BUY options (Long Gamma)
                contract_type = "CE" if proposal.action == "BUY" else "PE"
                
                # We need to map "Short Spot" to "Long Put"
                # If Action is SELL, we Buy PE. If Action is BUY, we Buy CE.
                
                # Map Symbol
                tradin_sym = options_mapper.get_symbol(proposal.symbol, current_price, proposal.action)
                
                logger.info(f"Planner: Mapped {proposal.symbol} {proposal.action} -> {tradin_sym} (Long Option)")
                proposal_action = "BUY" # We are buying the option
            else:
                proposal_action = proposal.action

            # Define SL/TP if not passed
            # In V1, we calculate standardized bracket if strategy didn't provide specific levels
            sl_price = current_price * 0.99 if proposal_action == "BUY" else current_price * 1.01
            tp_price = current_price * 1.02 if proposal_action == "BUY" else current_price * 0.98

            final_plan = TradePlan(
                plan_id=f"PLAN_{uuid.uuid4().hex[:8]}", # 17.1 Audit Fix: Collision proof
                symbol=tradin_sym,
                side=proposal_action,
                quantity=qty,
                limit_price=current_price, # Market entry approximation
                stop_loss=sl_price,
                take_profit=tp_price,
                plan_code="A",
                status="PENDING",
                confidence=proposal.confidence,
                features=proposal.features
            )
            # 17.2 Zero-Discrepancy Check
            Auditor.audit_plan_integrity(final_plan)
            return final_plan
        
        # Handle other plans (B-I)
        elif proposal.plan_type in ["B", "C", "D", "E", "F", "G", "H", "I"]:
            # Plans B-I: Advanced Recovery/Hedging/Scaling
            # For now, we map them to Standard Execution but Log distinct Plan Code
            # This ensures they are "In the Picture" and traceable.
            logger.info(f"Planner: Activating Advanced {proposal.plan_type} Logic for {proposal.symbol}")
            
            # Default to standard bracket for now
            sl_price = current_price * 0.99 if proposal.action == "BUY" else current_price * 1.01
            tp_price = current_price * 1.02 if proposal.action == "BUY" else current_price * 0.98

            return TradePlan(
                plan_id=f"PLAN_{proposal.plan_type}_{uuid.uuid4().hex[:8]}",
                symbol=proposal.symbol,
                side=proposal.action,
                quantity=qty,
                limit_price=current_price,
                stop_loss=sl_price,
                take_profit=tp_price,
                plan_code=proposal.plan_type, # Preserves B-I identity
                status="PENDING",
                confidence=proposal.confidence,
                features=proposal.features
            )

        # Handle other plans (J)
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
