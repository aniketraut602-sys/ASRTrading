#!/bin/bash

# ASR Trading - One-Click Server Setup Script
# Works on Ubuntu 20.04+ / Debian 12+ (GCP/AWS/Oracle)

set -e # Exit on error

echo "=== ASR Trading Server Setup ==="
echo "Operating System: $(lsb_release -d | cut -f2)"

# 1. Update System
echo "[1/5] Updating System Packages..."
# Prevent interactive prompts
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y docker.io git python3-pip python3-venv htop jq curl

# 2. Setup Project Directory
echo "[2/5] Setting up Directory..."
INSTALL_DIR="/opt/asr_trading"

# Create dir if not exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating install directory..."
    sudo mkdir -p $INSTALL_DIR
    sudo chown $USER:$USER $INSTALL_DIR
fi

# Permissions fix (ensure user owns it)
sudo chown -R $USER:$USER $INSTALL_DIR

# 3. Code Sync (Git or Copy)
# If it's a git repo, pull. If not, we assume files are uploaded via SCP/rsync.
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Git repository detected. Pulling latest changes..."
    cd $INSTALL_DIR
    git pull
else
    echo "No Git repository found at $INSTALL_DIR. Assuming files are transferred manually."
fi

cd $INSTALL_DIR

# 4. Virtual Environment (Idempotent)
echo "[3/5] Checking Virtual Environment..."
if [ ! -d "venv" ]; then
    echo "Creating venv..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "WARNING: requirements.txt not found!"
fi

# 5. Secrets Management (GCP Secret Manager Integration)
echo "[4/5] Checking Configuration..."
if [ ! -f ".env" ]; then
    echo ".env not found. Attempting to fetch from GCP Secret Manager..."
    
    # Check if gcloud is available and configured
    if command -v gcloud &> /dev/null; then
        echo "Fetching secrets..."
        # Try to fetch secrets. Fail gracefully if not configured or permission denied.
        set +e
        TG_TOKEN=$(gcloud secrets versions access latest --secret="asr_telegram_token" --quiet 2>/dev/null)
        GROWW_KEY=$(gcloud secrets versions access latest --secret="asr_groww_api_key" --quiet 2>/dev/null)
        GROWW_SECRET=$(gcloud secrets versions access latest --secret="asr_groww_api_secret" --quiet 2>/dev/null)
        set -e
        
        if [ -n "$TG_TOKEN" ] && [ -n "$GROWW_KEY" ]; then
             cat > .env <<EOF
TELEGRAM_BOT_TOKEN=$TG_TOKEN
GROWW_API_KEY=$GROWW_KEY
GROWW_API_SECRET=$GROWW_SECRET
BROKER_MODE=PAPER
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
EOF
             echo "Secrets fetched and .env created successfully."
        else
             echo "Could not fetch secrets. Creating from example."
             cp .env.example .env
             echo "WARNING: Please edit .env manually!"
        fi
    else
        echo "gcloud not found. creating default .env"
        cp .env.example .env
    fi
else
    echo ".env exists. Skipping generation."
fi

# 6. Service Management (Idempotent)
echo "[5/5] Configuring background service..."

SERVICE_FILE="/etc/systemd/system/asr_trading.service"
NEEDS_RELOAD=false

# Check if service file content differs or doesn't exist
# We construct the content to compare/write
read -r -d '' SERVICE_CONTENT <<EOF
[Unit]
Description=ASR Trading Engine
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run_paper.py
Restart=always
RestartSec=10
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

if [ ! -f "$SERVICE_FILE" ]; then
    echo "Creating service file..."
    echo "$SERVICE_CONTENT" | sudo tee $SERVICE_FILE > /dev/null
    NEEDS_RELOAD=true
else
    # Simple check if content changed (not perfect but sufficient)
    # Actually, let's just overwrite to be sure. It's cheap.
    echo "$SERVICE_CONTENT" | sudo tee $SERVICE_FILE > /dev/null
    NEEDS_RELOAD=true
fi

if [ "$NEEDS_RELOAD" = true ]; then
    sudo systemctl daemon-reload
    sudo systemctl enable asr_trading
fi

echo "=== Setup Complete! ==="
echo "Service is NOT auto-started yet to allow config verification."
echo "To START: sudo systemctl start asr_trading"
echo "To CHECK: systemctl status asr_trading"
