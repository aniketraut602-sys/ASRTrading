import unittest
import asyncio
from asr_trading.ops.monitoring import monitoring_agent
from asr_trading.web.telegram_v2 import notification_agent
from asr_trading.ops.audit_agent import audit_agent
from asr_trading.core.security import audit_ledger

class TestPhase7Full(unittest.TestCase):
    def setUp(self):
        import os
        if os.path.exists("audit_ledger.jsonl"):
            os.remove("audit_ledger.jsonl")
        # Reset AuditLedger state
        audit_ledger.last_hash = "GENESIS_HASH_0000000000000000"

    def tearDown(self):
        import os
        if os.path.exists("audit_ledger.jsonl"):
            os.remove("audit_ledger.jsonl")

    def test_observability(self):
        print("--- Testing Phase 7: Production Ops ---")
        
        # 1. Monitoring
        metrics = monitoring_agent.export_metrics_prometheus()
        self.assertIn("asr_uptime_seconds", metrics)
        print("    -> Monitoring: Prometheus metrics active.")
        
        # 2. Notification (Telegram)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        res = loop.run_until_complete(notification_agent.handle_command("/status"))
        self.assertIn("System Nominal", res)
        print("    -> Notification: '/status' command OK.")

        res_halt = loop.run_until_complete(notification_agent.handle_command("/halt"))
        self.assertIn("SYSTEM HALTED", res_halt)
        print("    -> Notification: '/halt' triggered emergency response.")
        
        # 3. Audit Ledger
        # Populate some data
        audit_ledger.record_event("TEST_EVENT", "SYS", {"action": "LOGIN"})
        audit_ledger.record_event("TEST_EVENT_2", "SYS", {"action": "TRADE"})
        
        # Verify Integrity (Positive)
        is_valid = audit_agent.run_integrity_check()
        self.assertTrue(is_valid)
        print("    -> Audit: Integrity Check PASSED.")
        
        # Tamper with Ledger (Negative Test - File Based)
        # We need to corrupt the file on disk since verifier reads form disk
        import json
        with open("audit_ledger.jsonl", "r") as f:
            lines = f.readlines()
        
        # Modify the last record's payload "TRADE" -> "HACKED" but keep hash same
        last_line = lines[-1]
        corrupted_line = last_line.replace("TRADE", "HACKED")
        lines[-1] = corrupted_line
        
        with open("audit_ledger.jsonl", "w") as f:
            f.writelines(lines)
        
        is_valid_bad = audit_agent.run_integrity_check()
        self.assertFalse(is_valid_bad)
        print("    -> Audit: Tampering DETECTED successfully.")
        
        print("--- Phase 7 Verified ---")

if __name__ == "__main__":
    unittest.main()
