import asyncio
from asr_trading.core.logger import logger
from asr_trading.data.canonical import Tick, OHLC
from asr_trading.data.ingestion import data_manager
from asr_trading.analysis.features import feature_engine
from asr_trading.strategy.selector import strategy_selector
from asr_trading.strategy.planner import planner_engine
from asr_trading.execution.execution_manager import execution_manager
from asr_trading.core.auditor import Auditor, InvariantViolation

class Orchestrator:
    """
    Manages the end-to-end trading lifecycle for a single symbol.
    Tick -> Features -> Strategy -> Plan -> Execution
    """
    
    async def run_cycle(self, symbol: str):
        """
        Executes one trading cycle for the given symbol.
        """
        try:
            # 1. Fetch Latest Data (Simulating Tick from last price for now)
            # In real system, this might be triggered by a Websocket Tick event directly
            price = data_manager.get_price(symbol) # Synchronous call to cache
            
            # Create a synthetic Tick for the audit pipeline
            tick = Tick(
                symbol=symbol, 
                last=price, 
                timestamp=int(asyncio.get_event_loop().time() * 1000), 
                volume=1000, # Mock volume if not available
                source="SCHEDULER",
                bid=price - 0.05,
                ask=price + 0.05, # minimal spread
                sequence=0
            )

            # 17.2 Audit: Tick Integrity
            Auditor.audit_tick_integrity(tick)
            
            # 2. Update Features (Simulate OHLC or fetch latest candle)
            # For now, we assume feature engine can compute from historical + latest tick
            # In a real event-driven system, this is cleaner. 
            # Here we push a dummy OHLC to trigger feature update
            dummy_ohlc = OHLC(symbol, tick.timestamp, price, price, price, price, 100, "1m")
            feature_result = feature_engine.on_ohlc(dummy_ohlc)
            
            if feature_result["status"] != "READY":
                logger.debug(f"Orchestrator [{symbol}]: Features not ready yet.")
                return

            features = feature_result["features"]

            # 3. Strategy Selection
            # We pass empty patterns list for now unless we integrate Pattern Recognition here too
            patterns = [] 
            proposal = strategy_selector.select_strategy(symbol, features, patterns, [])
            
            if not proposal:
                logger.debug(f"Orchestrator [{symbol}]: No strategy selected (HOLD).")
                return

            logger.info(f"Orchestrator [{symbol}]: Strategy PROPOSED -> {proposal.strategy_id} ({proposal.side})")

            # 4. Planning
            plan = planner_engine.create_plan(proposal, price)
            if not plan:
                logger.warning(f"Orchestrator [{symbol}]: Plan creation failed.")
                return

            # 5. Execution
            # Auditor check is inside execute_plan
            result = await execution_manager.execute_plan(plan)
            logger.info(f"Orchestrator [{symbol}]: Execution Result: {result['status']}")

        except InvariantViolation as iv:
            logger.critical(f"Orchestrator [{symbol}]: AUDIT FAILURE: {iv}")
        except Exception as e:
            logger.error(f"Orchestrator [{symbol}]: Cycle failed: {e}")

orchestrator = Orchestrator()
