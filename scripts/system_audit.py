import asyncio
import sys
import os

# Set Path
sys.path.append(os.getcwd())

from asr_trading.core.logger import logger

async def audit_data_layer():
    print("\n[Phase 1-5] Auditing Data Layer...")
    try:
        from asr_trading.data.scheduler import scheduler_service
        print("[OK] Data Scheduler Import: SUCCESS")
        # Check if configured
        if not scheduler_service.scheduler.running:
             print("   [WARN] Scheduler Not Running (Expected if offline)")
    except Exception as e:
        print(f"[FAIL] Data Layer FAILED: {e}")

async def audit_brain_layer():
    print("\n[Phase 6-10] Auditing Brain Layer...")
    try:
        from asr_trading.strategy.scalping import ScalpingStrategy
        from asr_trading.brain.learning import cortex
        print("[OK] Strategy Module Import: SUCCESS")
        print("[OK] Cortex (Learning) Import: SUCCESS")
    except Exception as e:
        print(f"[FAIL] Brain Layer FAILED: {e}")

async def audit_risk_layer():
    print("\n[Phase 11-15] Auditing Risk Layer...")
    try:
        from asr_trading.execution.risk_manager import risk_engine
        print(f"[OK] Risk Engine Active. Max Loss Pct: {risk_engine.profile.max_daily_loss_pct}")
    except Exception as e:
         print(f"[FAIL] Risk Layer FAILED: {e}")

async def audit_interface_layer():
    print("\n[Phase 16-19] Auditing Interface Layer...")
    try:
        from asr_trading.web.telegram_bot import linguistics
        from asr_trading.brain.llm_client import llm_brain
        print("[OK] Linguistics (Voice) Import: SUCCESS")
        print("[OK] LLM Client Import: SUCCESS")
    except Exception as e:
        print(f"[FAIL] Interface Layer FAILED: {e}")

async def run_full_audit():
    print("=== ASR TRADING SYSTEM INTEGRITY AUDIT (PHASES 1-19) ===")
    await audit_data_layer()
    await audit_brain_layer()
    await audit_risk_layer()
    await audit_interface_layer()
    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_full_audit())
