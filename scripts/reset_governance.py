import json
import os
import sys

STATS_PATH = "data/strategy_stats.json"

def reset_governance():
    print(f"[*] Governance Reset Tool Target: {STATS_PATH}")
    
    if not os.path.exists(STATS_PATH):
        print(f"[-] File {STATS_PATH} not found. Nothing to reset.")
        return

    try:
        with open(STATS_PATH, 'r') as f:
            data = json.load(f)
        
        print(f"[*] Found {len(data)} strategies.")
        
        updated = False
        for strat_id, stats in data.items():
            if stats.get("status") == "RETIRED" or stats.get("status") == "DRIFTING":
                print(f"    -> Resetting {strat_id} (Was {stats['status']})")
                stats["status"] = "ACTIVE"
                stats["wins"] = 0
                stats["trades"] = 0
                stats["history"] = []
                updated = True
                
        if updated:
            with open(STATS_PATH, 'w') as f:
                json.dump(data, f, indent=2)
            print("[+] Governance Reset COMPLETE. Governance memory wiped.")
        else:
            print("[*] No RETIRED strategies found.")

    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    reset_governance()
