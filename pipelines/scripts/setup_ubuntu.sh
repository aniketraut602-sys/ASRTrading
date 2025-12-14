#!/bin/bash

# ASR Trading - One-Click Server Setup Script
# Works on Ubuntu 20.04+ / Debian 12+ (GCP/AWS/Oracle)

set -e # Exit on error

echo "=== ASR Trading Server Setup ==="
echo "Operating System: $(lsb_release -d | cut -f2)"

# 1. Update System
echo "[1/5] Updating System Packages..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv git htop

# 2. Setup Project Directory
echo "[2/5] Setting up Directory..."
INSTALL_DIR="/opt/asr_trading"

# If current directory looks like the project, copy it. Else clone/empty.
# Assumption: User uploads zip content to ~ and runs script
if [ -d "$HOME/ASR_Trading" ]; then
    echo "Found uploaded files. Copying to $INSTALL_DIR..."
    sudo mkdir -p $INSTALL_DIR
    sudo cp -r $HOME/ASR_Trading/* $INSTALL_DIR/
else
    echo "No source files found. Creating empty dir at $INSTALL_DIR"
    sudo mkdir -p $INSTALL_DIR
    # We assume SCP will happen later or files are already there
fi

# Fix permissions
sudo chown -R $USER:$USER $INSTALL_DIR
cd $INSTALL_DIR

# 3. Virtual Environment
echo "[3/5] Creating Virtual Environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "WARNING: requirements.txt not found!"
fi

# 4. Create .env from example if missing
if [ ! -f ".env" ]; then
    echo "[4/5] Creating .env config..."
    cp .env.example .env
    echo "PLEASE EDIT .env WITH YOUR KEYS!"
fi

# 5. Setup Systemd Service (Auto-Start)
echo "[5/5] Creating 24/7 Background Service..."

SERVICE_FILE="/etc/systemd/system/asr_trading.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=ASR Trading Engine
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run_paper.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable asr_trading

echo "=== Setup Complete! ==="
echo "To START the engine: sudo systemctl start asr_trading"
echo "To STOP the engine:  sudo systemctl stop asr_trading"
echo "To VIEW LOGS:        journalctl -u asr_trading -f"
echo "To EDIT CONFIG:      nano $INSTALL_DIR/.env"
