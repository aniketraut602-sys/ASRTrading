import json
import hashlib
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from asr_trading.core.logger import logger

@dataclass
class ModelArtifact:
    model_id: str
    version: str
    model_type: str # "XGBOOST", "LSTM", "TRANSFORMER"
    path: str
    checksum: str
    metrics: Dict[str, float]
    status: str # "STAGING", "CANARY", "PRODUCTION", "ARCHIVED"
    rollout_pct: float = 0.0

class ModelRegistry:
    def __init__(self, registry_file="model_registry.json"):
        self.registry_file = registry_file
        self.models: Dict[str, ModelArtifact] = {}
        # In real life, load from disk

    def register_model(self, model_id: str, version: str, path: str, metrics: Dict[str, float]) -> ModelArtifact:
        # Calculate checksum stub
        checksum = hashlib.sha256(f"{model_id}:{version}".encode()).hexdigest()
        
        artifact = ModelArtifact(
            model_id=model_id,
            version=version,
            model_type="XGBOOST", # default for now
            path=path,
            checksum=checksum,
            metrics=metrics,
            status="STAGING",
            rollout_pct=0.0
        )
        self.models[f"{model_id}:{version}"] = artifact
        logger.info(f"MCP: Registered model {model_id}:{version} (Status: STAGING)")
        return artifact

    def promote_model(self, model_id: str, version: str, target_status: str, canary_pct: float = 0.0):
        key = f"{model_id}:{version}"
        if key in self.models:
            # Policy Check
            art = self.models[key]
            if target_status == "PRODUCTION":
                if art.metrics.get("accuracy", 0) < 0.6:
                    logger.warning(f"MCP: Policy Violation. Model accuracy < 0.6. Cannot promote {key}.")
                    return False
            
            art.status = target_status
            art.rollout_pct = canary_pct
            logger.info(f"MCP: Promoted {key} to {target_status} (Rollout: {canary_pct*100}%)")
            return True
        return False

    def get_production_model(self) -> Optional[ModelArtifact]:
        # Return the latest PRODUCTION model
        # Simple search
        for m in self.models.values():
            if m.status == "PRODUCTION":
                return m
        return None

mcp_agent = ModelRegistry()
