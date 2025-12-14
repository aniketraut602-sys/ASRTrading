import pytest
import time
from datetime import datetime, timezone
from asr_trading.data.canonical import Tick

def test_tick_timezone_logic():
    """
    Verify Tick.datetime_utc correctly handles naive/aware timestamps.
    """
    ts = 1700000000.0 # Some timestamp
    tick = Tick("TEST", ts, 100, 101, 100.5, 1000, "TEST", 1)
    
    dt = tick.datetime_utc
    assert dt.tzinfo == timezone.utc
    assert dt.timestamp() == ts

def test_tick_stale_check():
    """
    Verify is_stale Logic.
    """
    now = time.time()
    
    # Fresh Tick (1s old)
    tick_fresh = Tick("FRESH", now - 1.0, 100, 101, 100.5, 1000, "TEST", 1)
    assert tick_fresh.is_stale(threshold_sec=10.0) == False
    
    # Stale Tick (11s old)
    tick_stale = Tick("STALE", now - 11.0, 100, 101, 100.5, 1000, "TEST", 1)
    assert tick_stale.is_stale(threshold_sec=10.0) == True
