from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio
import time
from asr_trading.analysis.patterns import DetectedPattern
from asr_trading.core.logger import logger
from asr_trading.brain.learning import cortex
# Import Bot for Proactive Alerts
from asr_trading.web.telegram_bot import telegram_bot
from asr_trading.brain.governance import governance
from asr_trading.brain.regime import regime_monitor

@dataclass
class StrategyProposal:
    # ... (unchanged)
    strategy_id: str
    symbol: str
    action: str # BUY / SELL / HOLD
    confidence: float
    rationale: str
    rationale: str
    plan_type: str = "A" # Default Plan A
    volatility: float = 0.0 # 18.3 Capital Preservation: Pass context

class StrategySelector:
    """
    Evaluates market state (Features + Patterns + Knowledge) to propose a Strategy.
    """
    def __init__(self):
        self.monitoring_cache = {} # {symbol: timestamp}
        self.MONITOR_COOLDOWN = 300 # 5 minutes

    def _alert_monitoring(self, symbol: str, reason: str, features: Dict):
        """Async-safe trigger for monitoring alert"""
        now = time.time()
        last_alert = self.monitoring_cache.get(symbol, 0)
        
        if now - last_alert > self.MONITOR_COOLDOWN:
            self.monitoring_cache[symbol] = now
            # Fire and forget
            if telegram_bot.running:
                logger.info(f"Selector: Triggering Monitoring Alert for {symbol}")
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(telegram_bot.notify_monitoring(symbol, reason, features))
                except RuntimeError:
                    pass # No loop running

    def select_strategy(self, symbol: str, features: Dict, patterns: List[DetectedPattern], knowledge: List[Dict]) -> Optional[StrategyProposal]:
        """
        Main decision logic.
        """
    def select_strategy(self, symbol: str, features: Dict, patterns: List[DetectedPattern], knowledge: List[Dict]) -> Optional[StrategyProposal]:
        """
        Main decision logic.
        """
        # 1. Get ML Opinion (The "Smart" Part) - HARDENED
        # 18.2 Governance Check: Immediate Auto-Rejection of Retired Strategies
        # NOTE: This runs BEFORE the expensive ML prediction to save compute.
        if hasattr(cortex, 'governance'):
             # Note: cortex might not hold governance, we import it directly
             pass
        
        # We need the strategy_id to check governance, but here we are PROPOSING strategies.
        # So we check specific strategies as candidates.
        
        try:
            ml_prob = cortex.brain.predict_win_probability(features)
        except Exception as e:
            logger.error(f"Selector: ML Prediction failed for {symbol}: {e}. Defaulting to neutral (0.5).")
            ml_prob = 0.5

        # 18.5 Regime Fingerprinting
        regime_id = regime_monitor.detect_regime(features)
        preferred_strats = regime_monitor.get_preferred_strategies(regime_id)
        
        # Helper Factor
        def get_regime_modifier(strat_id):
            if strat_id in preferred_strats:
                return 0.1 # Boost
            elif preferred_strats: # If regime has preferences but this isn't one
                return -0.2 # Penalty
            return 0.0

        # 2. Check for Strong Patterns
        for p in patterns:
            if p.pattern_id == "CDL_HAMMER" and p.side == "BULLISH":
                # Check Knowledge
                k_conf = 1.0
                for k in knowledge:
                     if "CDL_HAMMER" in k["tags"]:
                         k_conf = k.get("confidence_modifier", 1.0)
                
                heuristic_conf = p.confidence * k_conf
                
                # Check Features (RSI < 30 for extra check?)
                # 17.1 Audit Fix: No implicit defaults for critical indicators
                if "RSI" not in features:
                    logger.debug(f"Selector: Missing RSI for Hammer Strategy on {symbol}. Skipping.")
                    continue
                    
                rsi = features["RSI"]
                if rsi < 40: # Oversold + Hammer = Strong Buy
                     heuristic_conf += 0.1
                
                # BLEND: 60% Heuristic, 40% ML (or 50/50)
                # 18.5 Regime Modifier
                final_conf = (heuristic_conf * 0.6) + (ml_prob * 0.4) + get_regime_modifier("STRAT_SCALP_HAMMER")
                
                if final_conf > 0.7:
                     # 18.2 Governance Check
                    strat_id = "STRAT_SCALP_HAMMER"
                    if not governance.is_allowed(strat_id):
                        logger.warning(f"Selector: Strategy {strat_id} is RETIRED. Action blocked.")
                    else:
                        return StrategyProposal(
                            strategy_id=strat_id,
                            symbol=symbol,
                            action="BUY",
                            confidence=min(final_conf, 0.99),
                            rationale=f"Hammer detected (RSI={rsi:.1f}). ML Agreement: {ml_prob:.2f}",
                            plan_type="A"
                        )
                elif final_conf > 0.5:
                     # MONITORING CASE
                     self._alert_monitoring(
                         symbol, 
                         f"Hammer detected but confidence ({final_conf:.2f}) is below threshold (0.7). Waiting for confirmation.",
                         {"RSI": f"{rsi:.1f}", "ML_Prob": f"{ml_prob:.2f}"}
                     )

        # 3. Check Momentum (EMA Crossover)
        # 17.1 Audit Fix: Validate Features
        if "MACD" not in features or "RSI" not in features:
            return None # Cannot evaluate momentum without MACD/RSI

        macd = features["MACD"]
        rsi = features["RSI"]
        
        if macd > 0 and rsi > 55:
             # Governance Check for Momentum
             if not governance.is_allowed("STRAT_MOMENTUM_V1"):
                 logger.debug("Selector: STRAT_MOMENTUM_V1 is RETIRED by Governance. Skipping.")
                 return None

             # Momentum Logic
             heuristic_conf = 0.75
             # 18.5 Regime Modifier
             final_conf = (heuristic_conf * 0.6) + (ml_prob * 0.4) + get_regime_modifier("STRAT_MOMENTUM_V1")
             
             if final_conf > 0.7:
                 return StrategyProposal(
                     strategy_id="STRAT_MOMENTUM_V1",
                     symbol=symbol,
                     action="BUY",
                     confidence=final_conf,
                     rationale=f"MACD positive crossover. ML Agreement: {ml_prob:.2f}",
                     plan_type="A"
                 )
             elif final_conf > 0.5:
                  # MONITORING CASE
                  self._alert_monitoring(
                      symbol,
                      f"Momentum building (MACD > 0) but not fully confirmed. Confidence: {final_conf:.2f}",
                      {"MACD": f"{macd:.2f}", "RSI": f"{rsi:.1f}"}
                  )

        return None

strategy_selector = StrategySelector()
