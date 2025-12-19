import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import threading
from asr_trading.core.config import cfg
import time
from asr_trading.core.logger import logger
from asr_trading.web.telegram_bot import telegram_bot
from asr_trading.core.avionics import avionics_monitor
from asr_trading.data.scheduler import scheduler_service
from asr_trading.core.cockpit import cockpit
# Avoid circular imports where possible, but we need these engines
from asr_trading.strategy.scalping import scalping_strategy

# --- Global State ---
SYSTEM_STATE = {
    "bot_active": False,
    "trading_paused": False,
}

# --- Pydantic Models (V1.1 Hardening) ---
from pydantic import BaseModel
from typing import List, Optional

from fastapi import Body

# class TradeRequest(BaseModel):
#     symbol: str
#     action: str = "BUY"
#     quantity: int = 1
#     confidence: float = 0.0
#     price: float = 0.0
#     confirm: bool = False # Required for LIVE trades

@app.post("/api/trade/validate")
async def validate_trade(trade: dict = Body(...)):
    """
    Validation Endpoint for UI 'Check Strategy'
    MOCK implementation for debugging 502.
    """
    # Safety accessor
    symbol = trade.get("symbol")
    action = trade.get("action", "BUY")
    quantity = trade.get("quantity", 1)
    price = trade.get("price", 0.0)

    # from asr_trading.strategy.planner import planner_engine
    
    return {
        "status": "VALID",
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "entry": price,
        "target": price * 1.02,
        "stop_loss": price * 0.99,
        "risk_reward": 2.0,
        "strategy": "Plan A (Mock)"
    }

@app.post("/api/trade/paper")
async def execute_paper_trade(trade: TradeRequest):
    """
    10. Execute Paper Trade (Via Real Framework)
    Input: TradeRequest Model
    Unified Execution: Re-uses PlannerEngine to ensure identical plan.
    """
    
    symbol = trade.symbol
    action = trade.action
    quantity = trade.quantity
    confidence = trade.confidence
    current_price = trade.price
    
    from asr_trading.execution.execution_manager import execution_manager
    from asr_trading.strategy.planner import planner_engine
    
    # Unified Execution: Re-generate the EXACT same plan using the engine
    # This prevents 'Manual' from side-stepping the Planner logic.
    plan = planner_engine.generate_proposal(
        strategy_id="MANUAL_EXECUTION", 
        symbol=symbol,
        action=action, 
        confidence=confidence,
        current_price=current_price
    )
    
    if not plan:
        return {"status": "ERROR", "message": "Execution Blocked by Planner/Risk Engine during final check."}
    
    # Set status to PENDING for execution
    plan.status = "PENDING"
    
    try:
        # Execute through REAL framework but force Paper Adapter
        # This validates Logic (Semi-Auto, Risk, etc) without Real Money
        result = await execution_manager.execute_plan(plan, force_paper=True)
    except Exception as e:
        logger.error(f"Server Execute Error: {e}")
        # Return proper error structure
        return {"status": "ERROR", "message": f"Execution Failed: {str(e)}"}
    
    status_msg = "SUCCESS" if "status" in result else "FAILED"
    cockpit.add_message(f"Paper Order: {result.get('status', 'Submitted')}", status_msg)
    
    return {
        "tradeId": plan.plan_id,
        "status": result.get("status"),
        "message": f"Paper Order Processed: {result.get('status')}",
        "raw_response": str(result)
    }

@app.post("/api/trade/validate")
async def validate_manual_trade(trade: TradeRequest):
    """
    8. Smart Manual Trade Validation (Unified Execution Check)
    Input: TradeRequest
    Output: Full 'PROPOSED' TradePlan with A-J params.
    """
    symbol = trade.symbol
    action = trade.action
    confidence = trade.confidence
    current_price = trade.price
    
    # 1. Generate Proposal via Real Analysis (Master Prompt Requirement)
    from asr_trading.strategy.planner import planner_engine
    from asr_trading.strategy.selector import strategy_selector
    from asr_trading.data.ingestion import data_manager 
    
    # Analyze Market State
    analysis = strategy_selector.analyze_on_demand(symbol, data_manager)
    
    if analysis:
        # Use System Conclusioin
        strat_id = analysis.strategy_id
        conf = analysis.confidence
        reason = analysis.rationale
        # If user override provided a higher confidence, maybe respect it? 
        # For now, strict system: system logic prevails unless we add an "Override" flag.
        if confidence > 0.0:
            # User provided explicit confidence, blend or override?
            # Enterprise Mode: Trust System, but allow user input to boost?
            # Let's simple use the MAX for now to allow user override if they see something system doesn't
            conf = max(conf, confidence) 
    else:
        # Fallback (System found nothing and crashed/timed out)
        strat_id = "MANUAL_FALLBACK"
        conf = confidence if confidence > 0.0 else 0.0
        reason = "Manual Input (System Analysis unavailable)"

    plan = planner_engine.generate_proposal(
        strategy_id=strat_id, 
        symbol=symbol,
        action=action, 
        confidence=conf,
        current_price=current_price
    )
    # Inject rationale if possible (Proposal object usually created inside generate_proposal)
    # Actually generate_proposal returns a plan. The plan object might not have rationale field exposed easily here.
    # But the Risk Check uses 'conf', which is now REAL.
    
    if not plan or plan.status == "REJECTED":
        reason = plan.rejection_reason if plan else "Risk Management Blocked Trade"
        return {
            "result": "REJECTED_RISK",
            "message": f"Risk Block: {reason}",
            "confidence": 0.0,
            "suggestion": "STOP",
            "risk_analysis": f"Hard Rejection: {reason}",
            "symbol": symbol,
            "price": current_price
        }
        
    return {
        "result": "VALID",
        "message": "Risk Checks Passed.",
        "confidence": plan.confidence,
        "suggestion": "STRONG BUY" if plan.side == "BUY" else "STRONG SELL",
        "risk_analysis": f"Plan A: SL @ {plan.stop_loss:.2f}, TP @ {plan.take_profit:.2f}. Risk: Approved.",
        "plan_details": {
            "id": plan.plan_id,
            "entry": plan.entry_price,
            "sl": plan.stop_loss,
            "tp": plan.take_profit,
            "size": plan.quantity
        },
        "symbol": symbol,
        "price": current_price
    }

@app.post("/api/trade/live")
async def execute_live_trade(trade: TradeRequest):
    """11. Execute Live Trade (Unified Flow)"""
    if not trade.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    
    symbol = trade.symbol
    action = trade.action
    quantity = trade.quantity
    confidence = trade.confidence
    current_price = trade.price
    
    from asr_trading.execution.execution_manager import execution_manager
    from asr_trading.strategy.planner import planner_engine
    
    # Unified Proposal Generation
    # This ensures Manual input goes through the same logic as Auto
    # Creating a proper Plan structure with SL/TP/Plan Code logic
    plan = planner_engine.generate_proposal(
        strategy_id="MANUAL_EXECUTION",
        symbol=symbol,
        action=action,
        confidence=confidence,
        current_price=current_price
    )

    if not plan:
        # Planner rejected it (e.g. Risk, Trading Paused)
        return {"status": "FAILED", "message": "Planner rejected proposal (Risk/Rules)"}
        
    # Override quantity with user input if needed (Planner might autosize)
    # But User input should be respected for Manual
    plan.quantity = quantity
    plan.plan_id = f"MANUAL_{plan.plan_id.split('_')[-1]}" # Tag as manual clearly

    # Execute Real
    # This will hit the SEMI-AUTO intercept in ExecutionManager if enabled
    result = await execution_manager.execute_plan(plan)
    
    status_msg = "SUCCESS" if "status" in result else "FAILED"
    cockpit.add_message(f"Manual Order: {result.get('status', 'Submitted')}", status_msg)
    
    return {
        "tradeId": plan.plan_id,
        "status": result.get("status"),
        "message": f"Order Processed: {result.get('status')}",
        "raw_response": str(result)
    }

    return {"status": "CANCEL_SAFE", "message": "Pending action cancelled safely"}

@app.get("/api/trade/pending")
async def get_pending_trades():
    """12b. Get Pending Approvals (Semi-Auto)"""
    from asr_trading.execution.execution_manager import execution_manager
    # Convert plan objects to dicts for JSON
    pending_list = []
    for pid, plan in execution_manager.pending_plans.items():
        pending_list.append({
            "plan_id": plan.plan_id,
            "symbol": plan.symbol,
            "action": plan.side,
            "quantity": plan.quantity,
            "strategy": plan.plan_code, # e.g. "A" or "MANUAL_EXECUTION"
            "confidence": plan.confidence,
            "sl": plan.stop_loss,
            "tp": plan.take_profit,
            "entry": plan.limit_price if plan.limit_price > 0 else plan.entry_price
        })
    return pending_list

@app.post("/api/trade/approve/{plan_id}")
async def approve_trade(plan_id: str):
    """12c. Approve Pending Trade"""
    from asr_trading.execution.execution_manager import execution_manager
    res = await execution_manager.confirm_execution(plan_id)
    if res.get("status") == "PLAN_NOT_FOUND_OR_EXPIRED":
        raise HTTPException(status_code=404, detail="Plan not found or expired")
    
    cockpit.add_message(f"Plan {plan_id} APPROVED via UI", "SUCCESS")
    return res

@app.post("/api/trade/reject/{plan_id}")
async def reject_trade(plan_id: str):
    """12d. Reject Pending Trade"""
    from asr_trading.execution.execution_manager import execution_manager
    if plan_id in execution_manager.pending_plans:
        del execution_manager.pending_plans[plan_id]
        cockpit.add_message(f"Plan {plan_id} REJECTED via UI", "WARNING")
        return {"status": "REJECTED", "message": "Trade plan rejected"}
    raise HTTPException(status_code=404, detail="Plan not found")



# F. BALANCE & RISK
@app.get("/api/account/balance")
async def get_balance():
    """13. Get balance & risk snapshot"""
    return {
        "availableBalance": cockpit.balance_available,
        "usedMargin": cockpit.margin_used,
        "openExposure": cockpit.exposure,
        "dailyRiskUsed": cockpit.daily_risk_used,
        "dailyRiskLimit": cfg.MAX_DAILY_LOSS,
        "message": "Balance and risk updated"
    }

@app.post("/api/account/refresh")
async def refresh_balance():
    """14. Refresh balance"""
    # Trigger async fetch here
    cockpit.add_message("Balance Refresh Requested", "INFO")
    return {"message": "Balance refreshed successfully"}

# G. DECISION EXPLANATION
@app.get("/api/decision/last")
async def get_last_decision():
    """15. Why trade taken or rejected"""
    return cockpit.last_decision

# H. LOGS & ALERTS
@app.get("/api/system/logs")
async def get_system_logs(limit: int = 50):
    """16. Get live system messages"""
    # Transform message list to simple strings for this specific contract if needed
    # User contract asks for ["Time Msg"...] format
    # Our internal is dicts, let's map it
    formatted_logs = [f"{m['timestamp']} {m['text']}" for m in cockpit.messages[-limit:]]
    return {"logs": formatted_logs}

@app.post("/api/settings/balance")
async def set_mock_balance(data: BalanceRequest):
    """18. Set Mock Balance (Paper Mode Only)"""
    if not cfg.IS_PAPER:
        raise HTTPException(status_code=400, detail="Mock balance only allowed in PAPER mode")
    
    amount = data.amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    cfg.CAPITAL = amount
    cockpit.balance_available = amount
    # Reset used margin/exposure for clean slate logic if needed, 
    # but for now just updating capital base is enough for the mock.
    
    cockpit.add_message(f"Mock Capital Updated: {amount}", "INFO")
    return {"status": "UPDATED", "capital": cfg.CAPITAL}

# I. EMERGENCY
@app.post("/api/system/kill")
async def kill_switch():
    """17. Emergency Kill Switch"""
    cockpit.add_message("EMERGENCY KILL", "CRITICAL")
    logger.critical("KILL SWITCH ACTIVATED")
    # Async kill
    asyncio.create_task(shutdown_server())
    return {"status": "HALTED", "message": "All trading halted immediately"}

async def shutdown_server():
    await asyncio.sleep(1)
    import signal
    os.kill(os.getpid(), signal.SIGINT)

# Serve Static
# --- DEBUG / DIAGNOSTICS ---
@app.get("/")
async def root_check():
    return {"status": "ONLINE", "version": cfg.VERSION, "message": "Root Route Reached"}

@app.exception_handler(404)
async def debug_404(request, exc):
    logger.error(f"DEBUG 404: {request.method} {request.url}")
    return {"status": "404", "detail": f"Route not found: {request.url.path}"}

# Serve Static (Moved to last)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
# Mount at /static to avoid conflicts with API
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
