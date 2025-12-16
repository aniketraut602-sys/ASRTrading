import asyncio
from datetime import datetime
from asr_trading.core.logger import logger
from asr_trading.data.canonical import Tick, OHLC
from asr_trading.data.feed_manager import feed_manager
from asr_trading.analysis.features import feature_engine
from asr_trading.strategy.selector import strategy_selector
from asr_trading.strategy.planner import planner_engine
from asr_trading.execution.execution_manager import execution_manager
from asr_trading.core.auditor import Auditor, InvariantViolation

from asr_trading.core.cockpit import cockpit

class Orchestrator:
    """
    Manages the end-to-end trading lifecycle for a single symbol.
    Tick -> Features -> Strategy -> Plan -> Execution
    """
    
    async def run_cycle(self, symbol: str):
        """
        Executes one trading cycle for the given symbol.
        """
        cockpit.update_activity("Scanning", f"Processing cycle for {symbol}...", symbol=symbol)
        
        try:
            # 1. Fetch Latest Data (Real Tick)
            tick = await feed_manager.get_tick(symbol)
            
            if not tick:
                cockpit.update_activity("Data Wait", "No data available.", symbol)
                return

            price = tick.last
            cockpit.update_activity("Analyzing", f"Price: {price}. Computing features...", symbol)
            
            # Audit (Already checked in FeedManager, but double check allowed)
            # Auditor.audit_tick_integrity(tick)

            # Audit
            Auditor.audit_tick_integrity(tick)
            
            # 2. Update Features
            dummy_ohlc = OHLC(symbol, tick.timestamp, price, price, price, price, 100, "1m")
            feature_result = feature_engine.on_ohlc(dummy_ohlc)
            
            if feature_result["status"] != "READY":
                msg = f"[{symbol}] Waiting for Data (Features not ready)"
                cockpit.update_activity("Waiting", msg, symbol)
                cockpit.add_message(msg, "WARNING")
                return

            features = feature_result["features"]

            # 3. Strategy Selection
            cockpit.update_activity("Evaluating", "Running strategy metrics...", symbol)
            patterns = [] 
            proposal = strategy_selector.select_strategy(symbol, features, patterns, [])
            
            if not proposal:
                cockpit.log_decision({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "symbol": symbol,
                    "action": "HOLD",
                    "reason": "Strategy filters not met.",
                    "confidence": 0,
                    "passed": ["Data Integrity"],
                    "failed": ["Signal Threshold"]
                })
                cockpit.update_activity("Idle", "No signal found.", symbol)
                cockpit.add_message(f"[{symbol}] Scan Complete: HOLD (No Strategy Trigger)", "INFO")
                return

            logger.info(f"Orchestrator [{symbol}]: Strategy PROPOSED -> {proposal.strategy_id} ({proposal.action})")
            
            # Update Cockpit with POSITIVE decision
            cockpit.log_decision({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "action": proposal.action,
                "reason": f"Strategy {proposal.strategy_id} triggers.",
                "confidence": proposal.confidence,
                "passed": ["Signal Threshold", "Risk Check (Prelim)"],
                "failed": []
            })

            # 4. Planning
            plan = planner_engine.create_plan(proposal, price)
            if not plan:
                logger.warning(f"Orchestrator [{symbol}]: Plan creation failed.")
                return

            # 5. Execution
            cockpit.update_activity("Executing", f"Submitting {proposal.action} order...", symbol)
            result = await execution_manager.execute_plan(plan)
            
            cockpit.add_message(f"Execution Result for {symbol}: {result['status']}", "SUCCESS" if result['status'] == "FILLED" else "WARNING")
            cockpit.update_activity("Idle", "Cycle complete.", symbol)

        except InvariantViolation as iv:
            logger.critical(f"Orchestrator [{symbol}]: AUDIT FAILURE: {iv}")
            cockpit.add_message(f"AUDIT FAILURE: {iv}", "ERROR")
        except Exception as e:
            logger.error(f"Orchestrator [{symbol}]: Cycle failed: {e}")
            cockpit.add_message(f"Cycle Error: {e}", "ERROR")

orchestrator = Orchestrator()
