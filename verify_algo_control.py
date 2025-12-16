import requests
import time

BASE_URL = "http://localhost:8000/api"

def run_test():
    print(">>> TESTING ALGO CONTROL PANEL API <<<")
    
    # 1. Check Initial Status
    try:
        s = requests.get(f"{BASE_URL}/system/status").json()
        print(f"[1] System Status: Monitor={s.get('monitor')}, Bot={s.get('telegramBot')}")
        if 'monitor' not in s:
            print("FAILED: 'monitor' key missing in status")
            return
    except Exception as e:
        print(f"FAILED: Connection error {e}")
        return

    # 2. Check Current Watchlist
    try:
        cur = requests.get(f"{BASE_URL}/monitor/current").json()
        print(f"[2] Current Config: {cur}")
    except Exception as e:
        print(f"FAILED: monitor/current error {e}")

    # 3. Update Watchlist
    new_wl = "INFY.NS, RELIANCE.NS, COALINDIA.NS"
    try:
        r = requests.post(f"{BASE_URL}/settings/watchlist", json={"symbols": new_wl})
        print(f"[3] Update Watchlist: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"FAILED: update watchlist error {e}")

    # 4. Verify Update
    try:
        cur = requests.get(f"{BASE_URL}/monitor/current").json()
        print(f"[4] Verified Config: {cur}")
        if "COALINDIA.NS" in cur.get("symbols", []):
             print("SUCCESS: Watchlist updated.")
        else:
             print("FAILED: Watchlist not updated.")
    except Exception as e:
        print(f"FAILED: verify update error {e}")
        
    # 5. Toggle Monitor Status
    try:
        # Stop first (ensure known state)
        requests.post(f"{BASE_URL}/monitor/stop")
        
        # Start
        requests.post(f"{BASE_URL}/monitor/start")
        time.sleep(1)
        s = requests.get(f"{BASE_URL}/system/status").json()
        print(f"[5] After Start: Monitor={s.get('monitor')}")
        
        if s.get('monitor') != "RUNNING":
             print("FAILED: Monitor should be RUNNING")
        
        # Stop
        requests.post(f"{BASE_URL}/monitor/stop")
        time.sleep(1)
        s = requests.get(f"{BASE_URL}/system/status").json()
        print(f"[6] After Stop: Monitor={s.get('monitor')}")
        
        if s.get('monitor') != "STOPPED":
             print("FAILED: Monitor should be STOPPED")
             
    except Exception as e:
         print(f"FAILED: Toggle monitor error {e}")

if __name__ == "__main__":
    run_test()
