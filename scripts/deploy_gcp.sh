#!/bin/bash
# ASR Trading - One Click GCP Deploy
# Usage: ./deploy_gcp.sh <PROJECT_ID>

PROJECT_ID=$1

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <PROJECT_ID>"
    exit 1
fi

echo "[Phase 19] Starting GCP Deployment for $PROJECT_ID..."

# 1. Verify Tools
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not found."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo "Error: terraform not found."
    exit 1
fi

# 2. Login Check
echo "Checking Auth..."
gcloud auth print-access-token > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Please login using: gcloud auth login"
    exit 1
fi
gcloud config set project $PROJECT_ID

# 3. Infra Deploy
echo "Deploying Infrastructure..."
cd infra
terraform init
terraform apply -var="project_id=$PROJECT_ID" -auto-approve
cd ..

# 4. Code Deploy (SCP approach since private git might be tricky without keys on server)
echo "Pushing Code to Server..."
IP=$(gcloud compute instances describe asr-trading-production --zone=asia-south1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Server IP: $IP"
echo "Waiting for SSH to be ready..."
sleep 30

# Using gcloud ssh to transfer files
# Exclude venv, .git, etc
echo "Syncing files..."
gcloud compute scp --recurse . asr-trading-production:~/asr_trading --zone=asia-south1-a --exclude=".git,.env,venv,__pycache__"

# 5. Remote Start
echo "Starting Application..."
gcloud compute ssh asr-trading-production --zone=asia-south1-a --command="cd ~/asr_trading && sudo bash pipelines/scripts/setup_ubuntu.sh && nohup python3 main.py > system.log 2>&1 &"

echo "DEPLOYMENT COMPLETE. ASR Trading is LIVE on $IP."
