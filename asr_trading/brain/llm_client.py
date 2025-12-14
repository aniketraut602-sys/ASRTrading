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

llm_brain = LLMClient()
