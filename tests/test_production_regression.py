import asyncio
import sys
import os
import time

# Add root to pythonpath
sys.path.append(os.getcwd())

from unittest.mock import MagicMock
from asr_trading.core.config import cfg
from asr_trading.core.logger import logger

# Mute logger
logger.setLevel("INFO")

async def test_regression_full_cycle():
    print("=== STARTING PRODUCTION REGRESSION ===")
    
    # 1. SETUP MOCKS
    from asr_trading.execution.execution_manager import execution_manager
    from asr_trading.execution.groww_adapter import GrowwAdapter
    
    adapter = GrowwAdapter()
    adapter.client = MagicMock()
    adapter.connected = True
    adapter.client.place_order.return_value = {"order_id": "REG_001"}
    adapter.client.get_order.side_effect = [
        {"orderId": "REG_001", "status": "REQUESTED"}, 
        {"orderId": "REG_001", "status": "COMPLETE", "filledQty": 100, "avgPrice": 101.5}
    ]
    
    # Force LIVE mode logic but with Mock Adapter
    cfg.IS_PAPER = False
    cfg.EXECUTION_TYPE = "AUTO" 
    execution_manager.set_brokers(adapter, None)
    
    # 2. SETUP ORCHESTRATOR & DATA
    from asr_trading.core.orchestrator import orchestrator
    from asr_trading.data.feed_manager import feed_manager
    from asr_trading.data.canonical import Tick
    
    # Inject Fake Tick
    mock_tick = Tick(
        symbol="REGTEST",
        timestamp=time.time(),
        last=100.0,
        bid=99.0,
        ask=100.0,
        volume=5000,
        source="MOCK",
        sequence=1
    )
    # Patch feed_manager.get_tick
    feed_manager.get_tick = MagicMock(return_value=asyncio.Future())
    feed_manager.get_tick.return_value.set_result(mock_tick)
    
    # 2b. Warmup Feature Engine (Or Mock it)
    from asr_trading.analysis.features import feature_engine
    # We patch `on_ohlc` to return READY features immediately
    feature_engine.on_ohlc = MagicMock(return_value={
        "status": "READY",
        "features": pd.DataFrame({"rsi": [30], "close": [100]}) # Mock Features
    })
    
    # 2c. Mock Strategy Selector to Force Signal
    from asr_trading.strategy.selector import strategy_selector
    from asr_trading.strategy.selector import StrategyProposal
    
    strategy_selector.select_strategy = MagicMock(return_value=StrategyProposal(
        strategy_id="TEST_STRAT",
        symbol="REGTEST",
        action="BUY",
        confidence=0.9,
        rationale="Regression Test Force",
        plan_type="A"
    ))
    
    # 3. RUN CYCLE (Signal -> Plan -> Execute)
    await orchestrator.run_cycle("REGTEST")
    
    # Verify Execution Called
    # Orchestrator calls execution_manager.execute_plan
    # execution_manager calls adapter.place_order
    adapter.client.place_order.assert_called()
    print("  -> Order Placed Successfully")
    
    # 4. VERIFY ORDER MANAGER STATE
    from asr_trading.execution.order_manager import order_engine
    
    if "REGTEST" not in order_engine.positions:
        print("FAIL: Order not registered in OrderManager")
        return
        
    status = order_engine.positions["REGTEST"]["status"]
    print(f"  -> Initial Order Status: {status}")
    if status != "SUBMITTED":
         print(f"FAIL: Expected SUBMITTED, got {status}")
         return

    # 5. RUN LIFECYCLE MONITOR (Sync Broker State)
    await order_engine.update_positions({}) # Loop 1: Check Pending -> Submitted
    await order_engine.update_positions({}) # Loop 2: Check -> Filled (due to side effect list)
    
    status = order_engine.positions["REGTEST"]["status"]
    print(f"  -> Final Order Status: {status}")
    if status != "FILLED":
         print(f"FAIL: Expected FILLED, got {status}")
         return
         
    # 6. VERIFY PNL MONITORING
    # Inject New Price via update_positions market_data arg
    # Entry was 101.5. TP is ~103.5. We send 105.0
    
    print("  -> Simulating TP Hit...")
    await order_engine.update_positions({"REGTEST": 105.0})
    
    if "REGTEST" in order_engine.positions:
        print("FAIL: Position should be closed (TP Hit)")
        return
        
    print("  -> Position Closed (TP Hit confirmed)")
    
    print("=== SUCCESS: FULL REGRESSION PASSED ===")

import pandas as pd
if __name__ == "__main__":
    asyncio.run(test_regression_full_cycle())
