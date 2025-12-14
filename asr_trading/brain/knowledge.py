import json
from typing import List, Dict, Optional
from asr_trading.core.logger import logger

# Simulation of a "Pre-fed Research Corpus"
INITIAL_CORPUS = [
    {
        "id": "KNO_001",
        "title": "Doji Reliability in Low Volatility",
        "tags": ["CDL_DOJI", "LOW_VOL"],
        "summary": "Doji candles in low volatility regimes often signal indecision but rarely immediate reversal without confirmation.",
        "confidence_modifier": 0.5
    },
    {
        "id": "KNO_002",
        "title": "Hammer Reversal Success Rate",
        "tags": ["CDL_HAMMER", "BULLISH"],
        "summary": "Hammer patterns at support levels have a 60% win rate in backtests (2020-2023).",
        "confidence_modifier": 1.2
    },
    {
        "id": "KNO_003",
        "title": "Bullish Engulfing Strategy",
        "tags": ["CDL_ENGULFING_BULL"],
        "summary": "Engulfing candles engulfing a prior 3-candle trend have highest probability.",
        "confidence_modifier": 1.5
    }
]

class KnowledgeManager:
    """
    Manages the Research Corpus and Retrieval.
    In vNext: Uses Vector DB (Pinecone/Chroma) for semantic search.
    Current: Tag-based retrieval.
    """
    def __init__(self):
        self.corpus = INITIAL_CORPUS
    
    def query(self, tags: List[str]) -> List[Dict]:
        """
        Retrieves knowledge items matching ANY of the tags.
        """
        results = []
        for item in self.corpus:
            # Check overlap
            if any(t in item["tags"] for t in tags):
                results.append(item)
        return results

    def add_knowledge(self, title: str, summary: str, tags: List[str]):
        new_item = {
            "id": f"KNO_{len(self.corpus) + 1:03d}",
            "title": title,
            "tags": tags,
            "summary": summary,
            "confidence_modifier": 1.0
        }
        self.corpus.append(new_item)
        logger.info(f"KnowledgeManager: Learned new item '{title}'")

knowledge_manager = KnowledgeManager()
