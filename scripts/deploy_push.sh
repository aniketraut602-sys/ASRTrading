#!/bin/bash
# DEPLOY PUSH (No Git Pull)

echo "=== ASR MANUALLY PUSHED DEPLOYMENT ==="

# 1. Install Deps
echo "[*] Installing Dependencies..."
pip3 install -r requirements.txt

# 2. Reset Governance
echo "[*] Resetting Governance..."
python3 scripts/reset_governance.py

# 3. Kill Old
echo "[*] Stopping Services..."
pkill -f python
pkill -f python3

# 4. Start
echo "[*] Starting Main..."
nohup python3 main.py > asr_trading.log 2>&1 &

echo "[✅] PUSH DEPLOY COMPLETE."
