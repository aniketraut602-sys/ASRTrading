import unittest
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

def run_suite():
    print("=== AIRCRAFT ACCEPTANCE: FULL SYSTEMS CHECK ===")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Phase 2: Data & redundancy (Gate 8.1)
    suite.addTests(loader.discover('tests', pattern='test_phase2_full.py'))
    
    # Phase 3: Features & Patterns (Gate 8.2)
    suite.addTests(loader.discover('tests', pattern='test_phase3_full.py'))
    
    # Phase 4: Execution & Risk (Gate 8.4, 8.5)
    suite.addTests(loader.discover('tests', pattern='test_phase4_full.py'))
    
    # Phase 6: MLOps (Gate 8.3)
    suite.addTests(loader.discover('tests', pattern='test_phase6_full.py'))
    
    # Phase 7: Ops & Audit (Gate 8.7, 8.10)
    suite.addTests(loader.discover('tests', pattern='test_phase7_full.py'))
    
    # Phase 8: Failed States (Gate 8.1 Disagreement, 8.6 Plan J)
    suite.addTests(loader.discover('tests', pattern='test_failed_states.py'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n=== GATE VERIFICATION REPORT ===")
    if result.wasSuccessful():
        print("[PASS] Gate 8.1: Data Integrity")
        print("[PASS] Gate 8.2: Feature/Pattern Parity")
        print("[PASS] Gate 8.3: Model Control Plane")
        print("[PASS] Gate 8.4: Idempotency")
        print("[PASS] Gate 8.5: Dual Routing")
        print("[PASS] Gate 8.6: Planner Plans (Plan J Verified)")
        print("[PASS] Gate 8.7: Security/Audit")
        print("[PASS] Gate 8.10: Observability")
        print("OVERALL STATUS: GREEN BOARD (READY FOR TAXI)")
        sys.exit(0)
    else:
        print("[FAIL] CRITICAL SYSTEMS FAILURE. GROUND AIRCRAFT.")
        sys.exit(1)

if __name__ == "__main__":
    run_suite()
