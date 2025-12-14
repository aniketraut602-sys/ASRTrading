# Endpoint Contract Matrix

## 1. Feature Engine -> Pattern Detector
**Contract**: `pandas.DataFrame` (OHLC + Indicators)
**Schema**:
```python
{
  "open": float, "high": float, "low": float, "close": float, "volume": float,
  "SMA_50": float, "RSI_14": float, "MACD": float, ...
}
```

## 2. Strategy Selector -> Planner
**Contract**: `StrategyProposal` Dataclass
**Schema**:
```python
@dataclass
class StrategyProposal:
    strategy_id: str  # e.g. "STRAT_SCALP_HAMMER"
    symbol: str       # "AAPL"
    action: str       # "BUY" | "SELL"
    confidence: float # 0.0 - 1.0
    rationale: str    # "Hammer detected..."
    plan_type: str    # "A"
```

## 3. Planner -> Execution Manager
**Contract**: `TradePlan` Dataclass
**Schema**:
```python
@dataclass
class TradePlan:
    plan_id: str      # Unique UUID
    symbol: str
    side: str         # "BUY" | "SELL"
    quantity: int
    limit_price: float
    stop_loss: float
    take_profit: float
    status: str
```

## 4. MCP -> Model Server
**Contract**: `ModelArtifact` Checksum
**Schema**:
```json
{
  "model_id": "M_XGB",
  "version": "v1.2",
  "checksum": "sha256:...",
  "path": "/models/v1.2.pkl"
}
```
