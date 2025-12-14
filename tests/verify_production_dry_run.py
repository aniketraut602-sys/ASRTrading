import unittest
import os
import sys
from asr_trading.core.config import cfg
from asr_trading.execution.risk_manager import risk_manager
from asr_trading.data.async_ingestion import data_nexus

class TestProductionDryRun(unittest.TestCase):
    
    def test_inr_config(self):
        """Verify Config matches INR Standards."""
        print(f"\n[Dry Run] Checking Config...")
        self.assertEqual(cfg.MAX_DAILY_LOSS, 5000.0, "MAX_DAILY_LOSS should be 5000 INR")
        self.assertEqual(cfg.MAX_POSITION_SIZE, 50000.0, "MAX_POSITION_SIZE should be 50000 INR")
        self.assertTrue("RELIANCE.NS" in cfg.WATCHLIST, "WATCHLIST should contain Indian stocks")
        print("[PASS] Config is standardized for INR.")

    def test_risk_manager_clean(self):
        """Verify Risk Manager has no mock capital."""
        print(f"\n[Dry Run] Checking Risk Manager...")
        # Check defaults
        self.assertEqual(risk_manager.total_capital, 100000.0, "RiskManager should default to 100k INR (Paper Default), not 10k.")
        print("[PASS] Risk Manager is clean.")

    def test_ingestion_clean(self):
        """Verify Ingestion has no mock providers."""
        print(f"\n[Dry Run] Checking Ingestion...")
        provider_names = [p.name for p in data_nexus.providers]
        self.assertNotIn("AlphaVantage", provider_names, "Mock AlphaVantage provider still present!")
        self.assertIn("Yahoo", provider_names, "Yahoo provider missing!")
        print("[PASS] Ingestion Providers: " + str(provider_names))

    def test_cleanup(self):
        """Verify deleted files."""
        print(f"\n[Dry Run] Checking File Cleanup...")
        exists = os.path.exists("asr_trading/brain/model_server.py")
        self.assertFalse(exists, "Legacy 'model_server.py' should have been deleted.")
        print("[PASS] Cleanup verified.")

if __name__ == '__main__':
    unittest.main()
