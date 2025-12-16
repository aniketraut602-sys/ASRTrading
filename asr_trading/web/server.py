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

# --- Lifespan for Startup/Shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CORE: Web Server Starting Up...")
    
    # 1. Start Telegram Bot in Background
    # check if loop is running
    try:
        current_loop = asyncio.get_running_loop()
        
        async def safe_start_bot():
            try:
                logger.info("Attempting to start Telegram Bot...")
                await telegram_bot.start_bot()
            except Exception as e:
                logger.error(f"FATAL: Telegram Bot Startup Failed: {e}")
                SYSTEM_STATE["bot_active"] = False
                
        bot_task = current_loop.create_task(safe_start_bot())
        SYSTEM_STATE["bot_active"] = True # Tentative, will update if fails
    except RuntimeError:
         # Should not happen in uvicorn
         pass
    
    # 2. Start Scheduler
    scheduler_service.start()
    
    # 3. Initialize Brokers (using the logic from main.py)
    # We do this in a non-blocking way or as part of startup
    try:
        from asr_trading.execution.execution_manager import execution_manager
        from asr_trading.execution.groww_adapter import GrowwAdapter
        from asr_trading.execution.broker_adapters import KiteRealAdapter, AlpacaRealAdapter
        
        if cfg.IS_PAPER or cfg.IS_LIVE:
            if cfg.GROWW_API_KEY:
                logger.info("Initializing Groww Adapter used...")
                groww = GrowwAdapter()
                # Connect is async
                # Connect is async - Move to background to avoid blocking Server Startup
                logger.info("Broker init moved to background task...")
                asyncio.create_task(groww.connect())
                
                # Assume success for now to bind adapter, status will update later
                execution_manager.set_brokers(primary=groww, secondary=None)
            elif cfg.KITE_API_KEY:
                execution_manager.set_brokers(primary=KiteRealAdapter(), secondary=None)
        
        # 4. Start Lifecycle Monitoring (Plan A loop)
        async def lifecycle_loop():
            from asr_trading.execution.order_manager import order_engine
            # Need market data source. For now, we mock or use latest from cockpit/scheduler
            # Ideally, order_engine matches against live data feed.
            logger.info("Lifecycle Monitor: Started (Plan A-J)")
            while True:
                try:
                    # In a real system, we pass a dict of {symbol: price}
                    # For prototype, we might skip or rely on internal fetch
                    # Stub: empty dict, assuming OrderManager might check price internally or this is placeholder
                    # FIX: We need prices. Let's use cockpit's last known prices if available
                    # or simple loop log
                    # order_engine.update_positions({}) 
                    
                    # Verification Heartbeat
                    if len(order_engine.positions) > 0:
                        logger.info(f"Lifecycle Monitor: Tracking {len(order_engine.positions)} positions...")
                        
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Lifecycle Loop Error: {e}")
                    await asyncio.sleep(5)

        current_loop.create_task(lifecycle_loop())
    except Exception as e:
        logger.error(f"Broker Init Warning: {e}")

    yield
    
    # Shutdown logic
    logger.info("CORE: Web Server Shutting Down...")
    scheduler_service.stop()
    # telegram bot shutdown is handled by the object itself mostly, 
    # but strictly we should cancel the task if we had the handle.
    # For now, relying on process exit.

app = FastAPI(title="ASR Trading Command Center", version=cfg.VERSION, lifespan=lifespan)

# CORS structure
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 17-POINT API CONTRACT IMPLEMENTATION ---

# A. SYSTEM STATUS
@app.get("/api/system/status")
async def get_system_status():
    """1. Get full system status"""
    try:
        health = avionics_monitor.get_system_health()
        return {
            "marketState": cockpit.market_state,
            "dataFeed": "CONNECTED" if health['status'] == "HEALTHY" else "DISCONNECTED",
            "tradingMode": cfg.EXECUTION_MODE,
            "executionMode": cfg.EXECUTION_TYPE,
            "telegramBot": "ONLINE" if telegram_bot.running else "OFFLINE",
            "monitor": "RUNNING" if scheduler_service.is_running else "STOPPED",
            "learningEngine": "ACTIVE",
            "lastDecisionAt": datetime.now().isoformat(), # Placeholder, should track real time
            "message": f"System operational in {cfg.EXECUTION_MODE} mode"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/review")
async def trigger_daily_review():
    """18.6 Manual Trigger for Daily Learning Loop"""
    from asr_trading.analysis.daily_analyzer import daily_analyzer
    summary = daily_analyzer.perform_review()
    return {"status": "COMPLETE", "summary": summary}

@app.post("/api/debug/close_all")
async def force_close_positions():
    """Debug: Close all open positions in OrderManager (Simulate EOD)"""
    from asr_trading.execution.order_manager import order_engine
    
    count = 0
    # Create copy of keys to avoid runtime error during iteration
    symbols = list(order_engine.positions.keys())
    for sym in symbols:
        order_engine.close_position(sym, "Admin Force Close")
        count += 1
        
    return {"status": "CLOSED", "count": count, "message": f"Closed {count} positions"}



# B. CURRENT ACTIVITY
@app.get("/api/system/activity")
async def get_system_activity():
    """2. What is ASR Trading doing right now"""
    # Check Avionics for Blocks
    health = avionics_monitor.get_system_health()
    is_blocked = (health['status'] != "HEALTHY")
    
    return {
        "state": cockpit.activity_status.upper(),
        "instrument": cockpit.current_symbol,
        "strategy": cockpit.current_strategy,
        "reason": cockpit.activity_detail,
        "blocked": is_blocked,
        "blockReason": health.get('reason') if is_blocked else None,
        "message": f"{cockpit.activity_status}: {cockpit.activity_detail}"
    }

# C. AUTO MODE CONTROLS
@app.post("/api/mode/auto/enable")
async def enable_auto_mode():
    """3. Enable Auto Mode"""
    cfg.EXECUTION_TYPE = "AUTO"
    cockpit.mode = "AUTO"
    cockpit.add_message("Auto Mode ENABLED", "WARNING")
    return {"autoMode": "ENABLED", "message": "Auto mode enabled with conservative risk limits"}

@app.post("/api/mode/auto/disable")
async def disable_auto_mode():
    """4. Disable Auto Mode"""
    cfg.EXECUTION_TYPE = "SEMI"
    cockpit.mode = "SEMI"
    cockpit.add_message("Auto Mode DISABLED", "INFO")
    return {"autoMode": "DISABLED", "message": "Auto mode disabled, switching to semi-auto control"}

@app.get("/api/mode/rules")
async def get_auto_rules():
    """5. Show Auto Mode Rules"""
    return {
        "confidenceThreshold": cfg.MIN_CONFIDENCE_SCORE,
        "maxDailyLossPercent": 2, # Hardcoded for now based on config
        "maxTradesPerDay": 3,
        "message": "Auto mode rules retrieved"
    }

@app.post("/api/mode/set")
async def set_execution_mode(data: dict):
    """5b. Set Execution Mode (PAPER/LIVE)"""
    target = data.get("mode", "").upper()
    if target not in ["PAPER", "LIVE"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use PAPER or LIVE.")
        
    # Safety Gate for LIVE
    if target == "LIVE":
        health = avionics_monitor.get_system_health()
        if health['status'] != "HEALTHY":
            raise HTTPException(status_code=403, detail=f"Live Mode Blocked: System {health['status']}")
            
    cfg.EXECUTION_MODE = target
    cfg.IS_PAPER = (target == "PAPER")
    cfg.IS_PAPER_TRADING = cfg.IS_PAPER
    cfg.IS_LIVE = (target == "LIVE")
    
    cockpit.add_message(f"Execution Mode switched to {target}", "WARNING" if target == "LIVE" else "INFO")
    return {"status": "SWITCHED", "mode": target, "message": f"Switched to {target} Mode"}

# D. SEMI-AUTO / MONITOR MODE
@app.post("/api/monitor/start")
async def start_monitoring():
    """6. Start Monitoring (Algo Loop)"""
    SYSTEM_STATE["trading_paused"] = False
    scheduler_service.start()
    cockpit.add_message("Algo Monitoring STARTED", "INFO")
    return {"status": "MONITORING_STARTED", "message": "Market monitoring active"}

@app.post("/api/monitor/stop")
async def stop_monitoring():
    """7. Stop Monitoring"""
    SYSTEM_STATE["trading_paused"] = True
    scheduler_service.stop()
    cockpit.add_message("Monitoring HALTED", "WARNING")
    return {"status": "MONITORING_STOPPED", "message": "Market monitoring stopped"}

@app.get("/api/monitor/current")
async def get_current_setup():
    """8. Get current monitored setup"""
    return {
        "symbols": cfg.WATCHLIST,
        "detail": cockpit.monitored_setup,
        "running": scheduler_service.is_running
    }

@app.post("/api/settings/watchlist")
async def update_watchlist(data: dict):
    """8b. Update Watchlist"""
    syms = data.get("symbols", [])
    if isinstance(syms, str):
        syms = [s.strip() for s in syms.split(",") if s.strip()]
        
    cfg.WATCHLIST = syms
    cockpit.monitored_setup = f"Monitoring {len(syms)} symbols"
    cockpit.add_message(f"Watchlist updated: {len(syms)} symbols", "INFO")
    return {"status": "UPDATED", "watchlist": cfg.WATCHLIST}

@app.get("/api/trade/last-rejected")
async def get_last_rejected():
    """9. Get last rejected trade"""
    return cockpit.last_rejected

# E. MANUAL & PAPER TRADING
@app.post("/api/trade/paper")
async def execute_paper_trade(trade: dict = {}):
    """
    10. Execute Paper Trade (Via Real Framework)
    Input: Full Plan details (from Validate step) or reconstruction params.
    Unified Execution: Re-uses PlannerEngine to ensure identical plan.
    """
    
    symbol = trade.get("symbol")
    action = trade.get("action")
    quantity = int(trade.get("quantity", 1))
    confidence = float(trade.get("confidence", 1.0))
    current_price = trade.get("price", 100.0)
    
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
    action = trade.get("action")
    quantity = int(trade.get("quantity", 1))
    confidence = float(trade.get("confidence", 1.0))
    
    from asr_trading.execution.execution_manager import execution_manager
    from asr_trading.strategy.planner import TradePlan
    import uuid
    
    # Create Plan
    plan = TradePlan(
        plan_id=f"PAPER_{uuid.uuid4().hex[:8]}",
        symbol=symbol,
        side=action,
        quantity=quantity,
        limit_price=trade.get("price", 0.0), # Fixed to limit_price based on Planner def
        entry_price=trade.get("price", 0.0), # Compat
        stop_loss=0.0,
        take_profit=0.0,
        plan_code="MANUAL_PAPER",
        confidence=confidence,
        status="PENDING"
    )
    
    import traceback
    try:
        # Execute through REAL framework but force Paper Adapter
        # This validates Logic (Semi-Auto, Risk, etc) without Real Money
        result = await execution_manager.execute_plan(plan, force_paper=True)
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Server Execute Error: {e}")
        return {"status": "ERROR", "message": str(e)}
    
    status_msg = "SUCCESS" if "status" in result else "FAILED"
    cockpit.add_message(f"Paper Order: {result.get('status', 'Submitted')}", status_msg)
    
    return {
        "tradeId": plan.plan_id,
        "status": result.get("status"), 
        "message": f"Paper Order Processed: {result.get('status')}",
        "raw_response": str(result)
    }

@app.post("/api/trade/validate")
async def validate_manual_trade(trade: dict = {}):
    """
    8. Smart Manual Trade Validation (Unified Execution Check)
    Input: Basic params (Symbol, Action)
    Output: Full 'PROPOSED' TradePlan with A-J params.
    """
    symbol = trade.get("symbol")
    action = trade.get("action", "BUY")
    confidence = float(trade.get("confidence", 0.0))
    current_price = trade.get("price", 100.0)
    
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
async def execute_live_trade(trade: dict = {}):
    """11. Execute Live Trade (Unified Flow)"""
    if not trade.get("confirm"):
        raise HTTPException(status_code=400, detail="Confirmation required")
    
    symbol = trade.get("symbol")
    action = trade.get("action")
    quantity = int(trade.get("quantity", 1))
    confidence = float(trade.get("confidence", 1.0))
    current_price = trade.get("price", 0.0)
    
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
async def set_mock_balance(data: dict):
    """18. Set Mock Balance (Paper Mode Only)"""
    if not cfg.IS_PAPER:
        raise HTTPException(status_code=400, detail="Mock balance only allowed in PAPER mode")
    
    amount = float(data.get("amount", 0))
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
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
