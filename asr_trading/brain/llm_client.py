import requests
import json
from asr_trading.core.logger import logger

class LLMClient:
    def __init__(self, model="llama3", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"

    def analyze_market(self, context_text: str) -> str:
        """
        Sends market context to local LLM and asks for analysis.
        """
        prompt = f"""
        You are a senior hedge fund trader. Analyze the following market data and provide a concise outlook (Bullish/Bearish/Neutral) and reasoning.
        
        DATA:
        {context_text}
        
        RESPONSE:
        """
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(self.api_url, json=payload)
            if response.status_code == 200:
                return response.json().get('response', 'Error parsing response')
            else:
                logger.error(f"LLM Error: {response.text}")
                return "LLM unavailable."
        except Exception as e:
            logger.error(f"LLM Connection Failed: {e}")
            return "LLM Connection Error (Is Ollama running?)"

    def chat(self, user_input: str) -> str:
        """
        General Conversation with Context Awareness.
        """
        system_prompt = (
            "You are the ASR Trading Agent, a sovereign production-grade trading system developed over 19 Phases.\n"
            "Your goal is to assist the operator with RCA (Root Cause Analysis), Status Checks, and Strategy Explanations.\n"
            "You are currently in Phase 19 (Go-Live). You are meticulous, professional, and slightly robotic but helpful.\n"
            "\n"
            "CONTEXT:\n"
            "- Phases 1-5: Core Data & Infrastructure (Stable)\n"
            "- Phases 6-10: Strategy & Brain (Scalping, Swing, LSTM)\n"
            "- Phases 11-15: Execution & Risk (Gatekeepers, Capital Preservation)\n"
            "- Phases 16-19: Interface & Monitoring (Telegram, Web UI, Dashboard)\n"
            "\n"
            "If asked about failures, suggest checking logs or running 'RCA'.\n"
            "Keep answers concise and text-based (no complex markdown tables)."
        )
        
        full_prompt = f"{system_prompt}\n\nUSER: {user_input}\nAGENT:"
        
        try:
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False
            }
            response = requests.post(self.api_url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json().get('response', 'Error parsing response')
            else:
                return f"[⚠ Brain Offline] Ollama returned {response.status_code}. Please check server."
        except Exception:
            return "[⚠ Brain Disconnected] Could not reach Ollama (localhost:11434). Is it running?"

llm_brain = LLMClient()
