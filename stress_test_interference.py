import requests
import threading
import time
import random

BASE_URL = "http://localhost:8000/api"

def buy_bot(i):
    try:
        # Using paper execute endpoint directly to bypass validation for speed
        r = requests.post(f"{BASE_URL}/trade/paper", json={
            "symbol": "TCS.NS",
            "action": "BUY",
            "quantity": 10,
            "confidence": 0.9
        })
        print(f"[{i}] BUY: {r.status_code}")
    except Exception as e:
        print(f"[{i}] BUY Error: {e}")

def sell_bot(i):
    try:
         # Simulate Algo Sell or Manual Sell
        r = requests.post(f"{BASE_URL}/trade/paper", json={
            "symbol": "TCS.NS",
            "action": "SELL",
            "quantity": 10,
            "confidence": 0.9
        })
        print(f"[{i}] SELL: {r.status_code}")
    except Exception as e:
        print(f"[{i}] SELL Error: {e}")

print("Starting HOSTILE INTERFERENCE TEST (Buy vs Sell Race)...")
requests.post(f"{BASE_URL}/mode/set", json={"mode": "PAPER"})
requests.post(f"{BASE_URL}/settings/balance", json={"amount": 100000})

threads = []
for i in range(20):
    t1 = threading.Thread(target=buy_bot, args=(i,))
    t2 = threading.Thread(target=sell_bot, args=(i,))
    threads.extend([t1, t2])

for t in threads:
    t.start()
    # No sleep - pure chaos attempt

for t in threads:
    t.join()

print("Interference Test Complete. Checking Balance...")
balance = requests.get(f"{BASE_URL}/account/balance").json()
print("Final Balance:", balance)
