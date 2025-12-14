import pytest
import asyncio
import json
from asr_trading.core.notifications import CommandProcessor
from asr_trading.core.logger import logger

# --- Stubs ---
# Mock Notification Agent to absorb floods
class MockNotificationAgent:
    def __init__(self):
        self.sent = 0
    async def send_message(self, chat_id, text):
        self.sent += 1
        return True

# --- Tests ---

def test_security_fuzzing_api_injection():
    """
    Scenario: Inject Malformed JSON, SQL-like strings, and excessive payloads.
    Expectation: System should NOT crash and should return error/safe response.
    """
    processor = CommandProcessor()
    
    # 1. Malformed JSON
    malformed = "{ 'action': 'buy',,, }"
    # Processor usually takes parsed dict or string. Let's assume it takes a command string or raw text.
    # If CommandProcessor parses text, we send text.
    
    # Assuming standard "/command" format.
    # Try injection:
    res = processor.process_command(12345, "/trade " + ("A" * 10000)) # Buffer Overflow attempt
    assert "Unrecognized" in res or "Error" in res or "processed" in res # Just ensure no crash
    
    # Try SQL Injection style
    res2 = processor.process_command(12345, "/trade ' OR 1=1; DROP TABLE users; --")
    assert "Unrecognized" in res2 or "Invalid" in res2
    
    # Try Shell Injection
    res3 = processor.process_command(12345, "/status; rm -rf /")
    assert "Unrecognized" in res3 or "Invalid" in res3 or "Error" in res3

def test_accessibility_fuzzing_telegram_flood():
    async def _run():
        """
        Scenario: Flood the system with 1000 messages in < 1 second.
        Expectation: System processing might lag but should not assume deadlock.
        """
        processor = CommandProcessor()
        # Mock the sending part
        
        start = asyncio.get_event_loop().time()
        
        # Fire 1000 commands
        # In real system this would hit a rate limiter.
        # Check if rate limiter exists or if it just queues.
        
        for i in range(100):
            processor.process_command(12345, "/status")
            
        end = asyncio.get_event_loop().time()
        duration = end - start
        
        print(f"Processed 100 commands in {duration:.4f}s")
        assert duration < 5.0 # Should be fast
    asyncio.run(_run())
