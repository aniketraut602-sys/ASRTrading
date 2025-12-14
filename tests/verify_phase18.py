import sys
import os
import asyncio
import time

# Add root to path
sys.path.append(os.getcwd())

from asr_trading.execution.execution_manager import execution_manager
from asr_trading.brain.governance import governance

async def verify_phase18():
    print("=== Phase 18 Verification: Survivability ===")
    
    strat_id = "STRAT_TEST_SURVIVAL"
    
    # 1. Reset Stats for Test Strat
    if strat_id in governance.stats:
        del governance.stats[strat_id]
    governance.save_stats()
    
    print(f"1. Initial State: {strat_id} Allowed? {governance.is_allowed(strat_id)}")
    assert governance.is_allowed(strat_id) == True
    
    # 2. Simulate 20 Losses
    print("\n2. Simulating 20 Losses...")
    for i in range(20):
        execution_manager.record_trade_result(
            plan_id=f"PLAN_{i}",
            strategy_id=strat_id,
            symbol="TESTUSDT",
            pnl=-10.0,
            outcome=0 # Loss
        )
        # Check status every 5
        if i % 5 == 0:
            print(f"   Trades: {i+1}, WinRate: {governance.stats.get(strat_id, {}).get('wins',0) / (i+1):.2f}")
            
    # 3. Check Governance
    print("\n3. Verifying Retirement...")
    is_allowed = governance.is_allowed(strat_id)
    status = governance.stats[strat_id]["status"]
    win_rate = governance.stats[strat_id]["wins"] / governance.stats[strat_id]["trades"]
    
    print(f"   Status: {status}")
    print(f"   Win Rate: {win_rate:.2f}")
    print(f"   Allowed: {is_allowed}")
    
    if is_allowed:
        print("FAIL: Strategy should be RETIRED but is still ALLOWED.")
        print(f"Threshold is {governance.RETIREMENT_THRESHOLD}")
        exit(1)
    else:
        print("PASS: Strategy was successfully RETIRED.")

    # 4. Clean up
    print("\n4. Cleanup")
    if strat_id in governance.stats:
        del governance.stats[strat_id]
        governance.save_stats()
    
    print("\n=== Phase 18 Verified ===")

if __name__ == "__main__":
    asyncio.run(verify_phase18())
