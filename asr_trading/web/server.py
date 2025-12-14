from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from asr_trading.core.config import cfg

app = FastAPI(title="ASR Trading Command Center", version=cfg.VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
def read_root():
    return {"status": "Online", "mode": cfg.EXECUTION_MODE}

@app.get("/api/signals")
def get_signals():
    # Placeholder: fetch from DB or Strategy Engine
    return [{"symbol": "AAPL", "action": "BUY", "confidence": 85}]

@app.get("/api/status")
def get_status():
    return {
        "reliability": 95.0,
        "positions_open": 2,
        "daily_pnl": 120.50
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
