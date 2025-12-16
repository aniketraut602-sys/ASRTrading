#!/bin/bash

# Deploy to GCP
# Usage: ./deploy_gcp.sh

set -e

# 1. Pre-flight checks
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not found."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
  echo "Error: terraform not found"
  exit 1
fi

echo "=== ASR Trading GCP Deployment ==="

# 2. Get Infrastructure Info
echo "Reading Terraform Output..."
cd infra
# Ensure we have state (assuming terraform apply was run)
# We use -raw to get just the string.
# Note: If terraform isn't applied, this fails.
# INSTANCE_IP=$(terraform output -raw public_ip 2>/dev/null || echo "")
INSTANCE_IP="35.244.6.241"


echo "Target Instance IP: $INSTANCE_IP"
cd ..

# 3. Deploy Code (SCM Sync)
# Strategy: SSH into box, git pull, rerun setup.

echo "Deploying to $INSTANCE_IP..."

# Assumes active gcloud login or SSH key setup.
# We'll use gcloud compute ssh for convenience as it handles keys.
# Zone is hardcoded or should be fetched.
ZONE="asia-south1-a"
INSTANCE_NAME="asr-trading-production"


echo "Creating deployment artifact..."
# Exclude venv, .git, and terraform state/config to keep transport light
# We use tar on the runner (Ubuntu) or local machine
tar --exclude='venv' --exclude='.git' --exclude='infra/.terraform' --exclude='infra/*.tfstate*' -czf deploy_artifact.tar.gz .

echo "Uploading artifact to $INSTANCE_NAME..."
# Upload to /tmp or home first
gcloud compute scp --zone "$ZONE" deploy_artifact.tar.gz "$INSTANCE_NAME":~/deploy_artifact.tar.gz

echo "Deploying & Restarting Service on Remote..."
gcloud compute ssh --zone "$ZONE" "$INSTANCE_NAME" --command "
    # 1. Clean/Prep Destination (Be careful not to delete config like .env)
    # We'll extract over existing files.
    
    # 2. Extract
    echo 'Extracting artifact...'
    sudo mkdir -p /opt/asr_trading
    sudo tar -xzf ~/deploy_artifact.tar.gz -C /opt/asr_trading
    
    # 3. Cleanup Artifact
    rm ~/deploy_artifact.tar.gz
    
    # 4. Fix Permissions
    sudo chown -R $USER:$USER /opt/asr_trading
    
    # 5. Run Setup (Updates venv, pip, etc)
    cd /opt/asr_trading
    sudo ./pipelines/scripts/setup_ubuntu.sh
    
    # 6. Restart Service
    sudo systemctl restart asr_trading
    
    # 7. Check Status
    systemctl status asr_trading --no-pager
"

# Cleanup local artifact
rm deploy_artifact.tar.gz


echo "=== Deployment Triggered Successfully ==="
