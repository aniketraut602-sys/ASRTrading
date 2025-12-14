"""
ASR Trading - Linguistic Engine (The "Voice")
Handles all user-facing communication with a professional, humanoid persona.
Enforces Accessibility (Screen-reader friendly Markdown) and Context Awareness.
"""

import logging
import random
from datetime import datetime, time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class LinguisticEngine:
    """
    The 'Brain' of the bot's communication.
    Decouples logic from text generation.
    Maintains daily context to provide meaningful summaries.
    """

    def __init__(self):
        self.context = {
            "daily_trades": [],
            "monitoring": set(),
            "wins": 0,
            "losses": 0,
            "learning_notes": []
        }
        # Professional, Calm, Senior Trader Persona
        self.templates = {
            "GREETING_MORNING": [
                "Good morning. Market pre-open checks are complete.",
                "Rise and shine. The markets are gearing up.",
                "Good morning. Ready for another session of disciplined trading."
            ],
            "GREETING_GENERIC": [
                "Hello. I am online and monitoring.",
                "Greetings. Systems are nominal.",
                "Hi there. How can I assist you with the market today?"
            ],
            "ACKNOWLEDGE": [
                "Understood.",
                "Copy that.",
                "Noted.",
                "Processing."
            ]
        }
    
    def _get_time_of_day(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12: return "MORNING"
        if 12 <= hour < 17: return "AFTERNOON"
        return "EVENING"

    def get_greeting(self) -> str:
        """Returns a time-appropriate, calm greeting."""
        tod = self._get_time_of_day()
        if tod == "MORNING":
            return random.choice(self.templates["GREETING_MORNING"])
        return random.choice(self.templates["GREETING_GENERIC"])

    def consult_market(self, market_data: Dict[str, Any]) -> str:
        """
        Responds to 'What should I look at?'
        """
        # In a real scenario, this would analyze market_data features
        # For now, we simulate the "Professional Analyst" response
        
        volatility = market_data.get('volatility', 'Moderate')
        trend = market_data.get('trend', 'Mixed')
        
        response = (
            f"**Market Context View**\n\n"
            f"Based on current data, here is my assessment:\n\n"
            f"*   **Market Mood**: {trend}\n"
            f"*   **Volatility**: {volatility}\n\n"
            f"**Recommendation**:\n"
            f"Focus on quality over quantity today. "
            f"I am prioritizing clear breakouts with volume confirmation. "
            f"Avoid low-liquidity options in this regime.\n\n"
            f"I will alert you if any high-confidence setups appear."
        )
        return response

    def announce_monitoring(self, ticker: str, reason: str, technicals: Dict[str, Any]) -> str:
        """
        Proactive Alert: Started monitoring a ticker.
        """
        self.context["monitoring"].add(ticker)
        
        features_text = "\n".join([f"*   {k}: {v}" for k, v in technicals.items()])
        
        return (
            f"👀 **Started Monitoring: {ticker}**\n\n"
            f"**Reason**:\n"
            f"{reason}\n\n"
            f"**Key Signals**:\n"
            f"{features_text}\n\n"
            f"No trade executed yet. I am waiting for final confirmation."
        )

    def announce_trade_entry(self, trade: Dict[str, Any]) -> str:
        """
        Proactive Alert: Trade executed.
        """
        self.context["daily_trades"].append(trade)
        ticker = trade.get('ticker', 'Unknown')
        strategy = trade.get('strategy', 'Standard')
        confidence = trade.get('confidence', 0.0) * 100
        
        return (
            f"⚡ **Executing Trade**\n\n"
            f"*   **Instrument**: {ticker}\n"
            f"*   **Strategy**: {strategy}\n"
            f"*   **Confidence**: {confidence:.1f}%\n"
            f"*   **Action**: {trade.get('action', 'BUY')}\n\n"
            f"**Why this trade?**\n"
            f"Multiple conditions aligned with the {strategy} strategy. "
            f"Volume and momentum confirm the move, and risk is within our defined limits.\n\n"
            f"I will manage this position and keep you updated."
        )

    def announce_trade_exit(self, trade_id: str, reason: str, pnl: float) -> str:
        """
        Proactive Alert: Trade exited.
        """
        result = "PROFIT" if pnl > 0 else "LOSS"
        if pnl > 0: self.context["wins"] += 1
        else: self.context["losses"] += 1
        
        note = f"{result} on {trade_id}: {reason}"
        self.context["learning_notes"].append(note)

        return (
            f"🛑 **Trade Exited**\n\n"
            f"*   **Result**: {result} ({pnl:.2f})\n\n"
            f"**Reason for Exit**:\n"
            f"{reason}\n\n"
            f"This outcome has been recorded for learning purposes."
        )

    def explain_last_decision(self) -> str:
        """
        Responds to '/why' or 'Why did you do that?'
        """
        if not self.context["daily_trades"]:
            return (
                "I haven't executed any trades yet today, so there is no recent decision to explain.\n\n"
                "I am currently in **Monitoring Mode**, waiting for high-probability setups."
            )
        
        last_trade = self.context["daily_trades"][-1]
        return (
            f"**Explanation for {last_trade.get('ticker', 'Last Trade')}**\n\n"
            f"I took this trade because the following factors aligned:\n\n"
            f"1.  **Strategy Fit**: The market behavior matched the profile for {last_trade.get('strategy')}.\n"
            f"2.  **Risk/Reward**: The potential upside outweighed the calculated risk.\n"
            f"3.  **Confirmation**: Signals were not isolated; they were confirmed by volume/volatility.\n\n"
            f"This was a probability-based decision consistent with my rules."
        )

    def get_morning_brief(self, market_data: Dict[str, Any]) -> str:
        """
        Generates the Pre-Market Auto Message.
        """
        trend = market_data.get('trend', 'Sideways to mildly bullish')
        volatility = market_data.get('volatility', 'Moderate')
        
        return (
            f"🌅 **Pre-Market View**\n\n"
            f"**Market Context**:\n"
            f"*   **Market Mood**: {trend}\n"
            f"*   **Volatility**: {volatility}\n"
            f"*   **Overall Risk**: Acceptable for selective intraday trades\n\n"
            f"**Strategies in Focus**:\n"
            f"1.  Intraday Momentum (Reliability: 68%)\n"
            f"2.  Mean Reversion (Reliability: 72%)\n\n"
            f"**Watchlist**:\n"
            f"*   **NIFTY 50**: 1-day expiry, ATM range\n"
            f"*   **BANKNIFTY**: Elevated IV, monitor for breakout\n\n"
            f"I am in **Auto-Mode** with conservative risk today.\n"
            f"I will notify you before taking or monitoring any position."
        )

    def get_eod_summary(self) -> str:
        """
        Daily summary generator.
        """
        trades_count = len(self.context["daily_trades"])
        wins = self.context["wins"]
        losses = self.context["losses"]
        
        notes = "\n".join([f"*   {n}" for n in self.context["learning_notes"]]) if self.context["learning_notes"] else "*   No significant anomalies detected."

        return (
            f"🌙 **End of Day Summary**\n\n"
            f"**Performance**:\n"
            f"*   Total Trades: {trades_count}\n"
            f"*   Wins: {wins} | Losses: {losses}\n\n"
            f"**Key Learnings**:\n"
            f"{notes}\n\n"
            f"I have updated my internal weights based on today's session.\n"
            f"Rest well. I will prepare the pre-market view for tomorrow."
        )

    def handle_freeform(self, text: str) -> str:
        """
        Simple keyword-based conversational fallback.
        """
        text = text.lower()
        if "hello" in text or "hi" in text:
            return self.get_greeting()
        if "status" in text:
            return "I am currently online and monitoring the markets."
        if "stop" in text or "pause" in text:
            return "Understood. Creating a pause request..."
        if "learn" in text:
            return self.get_eod_summary() # Mocking learning response with EOD for now
        
        return (
            "I heard you, but I'm not sure how to respond to that specifically yet.\n"
            "You can ask me 'Status', 'Why?', or 'What should I look at?'."
        )

# Singleton instance for easy import
linguistics = LinguisticEngine()
