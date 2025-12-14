# Redundancy & Avionics Wiring

## 1. Data Feed "Jumbo Jet" Redundancy
**Architecture**: Active Failover
**Logic**: Priority Chain (1 -> 2 -> 3 -> Cache)

| Tier | Provider | Failover Trigger | Recovery |
| :--- | :--- | :--- | :--- |
| **Primary** | Finnhub | Exception / Timeout > 2s | Auto-retry after 60s |
| **Secondary** | AlphaVantage | Primary Fails | Auto-standby |
| **Tertiary** | TwelveData | Secondary Fails | Auto-standby |
| **Last Resort**| Local Cache | Tertiary Fails | **DEGRADED MODE** |

**Wiring Verification**: 
- `tests/test_phase2_full.py` confirms fallback from P1 -> P2 -> P3 -> Cache.
- `tests/chaos_monkey.py` confirms resilience under simulated outages.

## 2. Dual-Execution Routing
**Architecture**: Hot-Hot (Conceptually), Active-Standby (implemented)
**Logic**: Try Primary; if rejected/timeout, try Secondary immediately.

| Tier | Broker | Role |
| :--- | :--- | :--- |
| **Primary** | Kite Connect | Main execution venue. |
| **Secondary** | Alpaca / IBKR | Backup venue. Used for liquidation or if Kite is down. |

**Idempotency**:
- Controlled by `ExecutionManager.used_plan_ids`.
- Prevents double execution if Primary times out but actually fills.
- **Protocol**: If Primary returns ambiguous error, check order status via Reconciliation Loop before sending to Secondary (Future enhancement). Current logic: Try Secondary on explicit Exception.
