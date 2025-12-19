@echo off
echo ===================================================
echo ASR TRADING - PRODUCTION DEPLOYMENT HELPER
echo ===================================================

echo [1] Checking Git Status...
git status

echo.
echo [2] Adding all production files...
git add .
git commit -m "chore: Final Pre-Deployment Cleanup (Deleted 15+ legacy tests, Added app.yaml)"

echo.
echo [3] Pushing to Remote Repository...
git push origin main

echo.
echo [4] DEPLOYMENT INSTRUCTIONS
echo ---------------------------------------------------
echo Since this terminal cannot execute 'gcloud', please
echo run the following command in your GCP Shell or authorized terminal:
echo.
echo    gcloud app deploy
echo.
echo This will use the new 'app.yaml' I just created.
echo ---------------------------------------------------
echo.
pause
