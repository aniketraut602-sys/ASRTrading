#!/bin/bash

echo "=== ASR TRADING DEPLOY FIX & RECOVERY ==="
echo "Date: $(date)"

# 1. Update Code
echo "[*] Pulling latest code..."
git pull origin main

# 2. Run Prevention/Cleanup
echo "[*] Resetting Governance (System Unlock)..."
python3 scripts/reset_governance.py

# 3. Kill Zombies
echo "[*] Stopping Stale Processes..."
pkill -f python
pkill -f python3

# 4. Restart Logic (Assuming systemd or manual)
if systemctl is-active --quiet asr_trading; then
    echo "[*] Restarting Systemd Service..."
    sudo systemctl restart asr_trading
else
    echo "[*] Starting Manual Process (nohup)..."
    nohup python3 main.py > asr_trading.log 2>&1 &
fi

echo "[✅] DEPLOYMENT COMPLETE. System should be Online."
echo "Verify by sending /start to the Telegram Bot."
