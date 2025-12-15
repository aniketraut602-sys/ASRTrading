from asr_trading.brain.learning import cortex
from asr_trading.core.logger import logger

class EnsembleAgent:
    """
    Combines Signals.
    """
    def __init__(self, w_rule=0.6, w_model=0.4):
        self.w_rule = w_rule
        self.w_model = w_model

    def calculate_ensemble_score(self, rule_conf: float, features: dict) -> float:
        """
        Returns weighted probability.
        """
        # Get Model Prediction
        # Ensure model is fresh
        cortex.brain.load_model()
        model_prob = cortex.brain.predict_win_probability(features)
        
        # Weighted Avg of Probabilities (assuming rule_conf is a prob 0-1)
        final_score = (self.w_rule * rule_conf) + (self.w_model * model_prob)
        
        logger.debug(f"Ensemble: Rule={rule_conf:.2f}, Model={model_prob:.2f} -> Final={final_score:.2f}")
        return final_score

ensemble_agent = EnsembleAgent()
