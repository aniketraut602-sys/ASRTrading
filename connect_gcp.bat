@echo off
REM Easy Connect to ASR Trading Server
echo Connecting to GCP Server...
powershell -ExecutionPolicy Bypass -Command "gcloud compute ssh asr-trading-production --zone=asia-south1-a"
