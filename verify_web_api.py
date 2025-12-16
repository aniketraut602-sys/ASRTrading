import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_api():
    print("--- API VERIFICATION ---")
    
    # 1. Check Status
    try:
        r = requests.get(f"{BASE_URL}/api/system/status")
        print(f"[STATUS] {r.json().get('tradingMode')}")
    except Exception as e:
        print(f"Server down? {e}")
        return
        
    # 2. Switch to LIVE (Verify Gate) - Should likely fail if healthy check blocks, or pass
    # Doing Paper mostly
    
    # 3. Switch to PAPER
    print("\n[STEP] Switching to PAPER...")
    r = requests.post(f"{BASE_URL}/api/mode/set", json={"mode": "PAPER"})
    print(f"Response: {r.status_code} {r.text}")
    if r.status_code != 200:
        print("FAIL: Could not switch to PAPER")
        sys.exit(1)
        
    # 4. Set Mock Balance
    print("\n[STEP] Setting Mock Balance to 500k...")
    r = requests.post(f"{BASE_URL}/api/settings/balance", json={"amount": 500000})
    print(f"Response: {r.status_code} {r.text}")
    if r.status_code != 200:
        print("FAIL: Could not set balance")
        sys.exit(1)
        
    # 5. Verify Balance
    print("\n[STEP] Verifying Balance...")
    r = requests.get(f"{BASE_URL}/api/account/balance")
    bal = r.json().get("availableBalance")
    print(f"Balance: {bal}")
    if bal == 500000:
        print("SUCCESS: Balance Updated.")
    else:
        print("FAIL: Balance mismatch.")
        sys.exit(1)
        
    print("\n--- API VERIFICATION PASSED ---")

if __name__ == "__main__":
    test_api()
