import asyncio
import logging
import unittest.mock
from unittest.mock import MagicMock, AsyncMock
from asr_trading.web.telegram_bot import telegram_bot
from asr_trading.core.config import cfg

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def test_bot_logic():
    print("--- TELEGRAM LOGIC VERIFICATION ---")
    
    # 0. Setup Mock Capital for Testing
    cfg.CAPITAL = 1000000.0  # Ensure sufficient capital
    
    # Mock Update and Context
    update = MagicMock()
    update.effective_user.id = cfg.TELEGRAM_ADMIN_ID # Auth
    update.message.reply_text = AsyncMock()
    
    context = MagicMock()
    context.user_data = {} # Simulating context storage
    
    # 1. Test Mode Switching
    print("\n[TEST 1] Switch to PAPER Mode")
    update.message.text = "paper mode"
    await telegram_bot._handle_text(update, context)
    
    if cfg.EXECUTION_MODE == "PAPER" and cfg.IS_PAPER_TRADING:
        print("SUCCESS: Mode switched to PAPER.")
    else:
        print(f"FAIL: Mode is {cfg.EXECUTION_MODE}")
        return

    # 2. Test Strategy Check (NIFTY)
    print("\n[TEST 2] Strategy Check 'NIFTY'")
    
    # Mock Planner Engine to bypass Risk checks for Telegram Logic verification
    from asr_trading.strategy.planner import TradePlan
    dummy_plan = TradePlan(
        plan_id="TEST_PLAN_123",
        symbol="NIFTY",
        side="BUY",
        quantity=1,
        entry_price=100.0,
        limit_price=100.0,
        stop_loss=90.0,
        take_profit=120.0,
        plan_code="A",
        status="PROPOSED",
        confidence=0.9
    )
    
    # Mock Planner Engine to bypass Risk checks for Telegram Logic verification
    # UPDATE: We now have sufficient capital in config, so we can test REAL logic
    # from asr_trading.strategy.planner import TradePlan
    
    # Real Call
    update.message.text = "check strategy nifty"
    await telegram_bot._handle_text(update, context)
    
    # Verify Pending Proposal
    if 'pending_proposal' in context.user_data:
        plan = context.user_data['pending_proposal']
        print(f"SUCCESS: Proposal Generated: {plan.symbol} {plan.side}")
    else:
        print("FAIL: No proposal generated.")
        return

    # 3. Test Execution Confirmation
    print("\n[TEST 3] Execute 'OK'")
    update.message.text = "ok"
    # Mock execution_manager.execute_plan to avoid actual API calls/failures
    # But wait, we want integration test? 
    # Calling execute_plan actually hits the Broker Adapter.
    # Paper Adapter should accept it.
    
    await telegram_bot._handle_text(update, context)
    
    # Verify Context Cleared
    if 'pending_proposal' not in context.user_data:
        print("SUCCESS: Proposal executed and context cleared.")
    else:
        print("FAIL: Context not cleared.")

    print("\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(test_bot_logic())
