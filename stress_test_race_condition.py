import requests
import threading
import time
import random

BASE_URL = "http://localhost:8000/api"

def toggle_mode(i):
    mode = "LIVE" if i % 2 == 0 else "PAPER"
    try:
        r = requests.post(f"{BASE_URL}/mode/set", json={"mode": mode})
        print(f"[{i}] Set Mode {mode}: {r.status_code}")
    except Exception as e:
        print(f"[{i}] Mode Error: {e}")

def spam_trade(i):
    try:
        r = requests.post(f"{BASE_URL}/trade/validate", json={"symbol": "TCS.NS", "action": "BUY"})
        print(f"[{i}] Trade Check: {r.status_code}")
    except Exception as e:
        print(f"[{i}] Trade Error: {e}")

def spam_monitor(i):
    action = "start" if i % 2 == 0 else "stop"
    try:
        r = requests.post(f"{BASE_URL}/monitor/{action}")
        print(f"[{i}] Monitor {action}: {r.status_code}")
    except Exception as e:
        print(f"[{i}] Monitor Error: {e}")

threads = []
print("Starting HOSTILE RACE CONDITION TEST...")

# Launch 20 concurrent threads doing conflicting things
for i in range(20):
    t1 = threading.Thread(target=toggle_mode, args=(i,))
    t2 = threading.Thread(target=spam_trade, args=(i,))
    t3 = threading.Thread(target=spam_monitor, args=(i,))
    threads.extend([t1, t2, t3])

for t in threads:
    t.start()
    time.sleep(0.05) # Slight stagger to hit server processing

for t in threads:
    t.join()

print("Trace complete. Checking Final State...")
# Verify consistency at end
status = requests.get(f"{BASE_URL}/system/status").json()
print("Final Status:", status)

balance = requests.get(f"{BASE_URL}/account/balance").json()
print("Final Balance:", balance)
