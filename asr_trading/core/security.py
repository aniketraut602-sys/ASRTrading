import os
import hashlib
import json
import time
import threading
from typing import Optional
from asr_trading.core.logger import logger

class SecurityException(Exception):
    pass

class SecretsManager:
    """
    Centralized access to sensitive credentials.
    In Production, this should interface with HashiCorp Vault or AWS Secrets Manager.
    For now, it wraps environment variables with strict validation.
    """
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None, required: bool = True) -> str:
        val = os.environ.get(key, default)
        if required and not val:
            logger.critical(f"Security: Missing required secret '{key}'.")
            raise SecurityException(f"Missing required secret: {key}")
        if val and key.lower().endswith("token") or key.lower().endswith("key"):
            # Mask in logs if we ever logged it (we shouldn't)
            pass
        return val

class AuditLedger:
    """
    Immutable, Append-Only Ledger for critical trade events.
    Each entry includes a hash of the previous entry to create a tamper-evident chain.
    """
    def __init__(self, ledger_file="audit_ledger.jsonl"):
        self.ledger_file = ledger_file
        self.lock = threading.Lock()
        
        # Initialize or Load last hash
        self.last_hash = "GENESIS_HASH_0000000000000000"
        self._recover_last_hash()

    def _recover_last_hash(self):
        """Reads the file to find the last hash on startup."""
        if not os.path.exists(self.ledger_file):
            return

        with open(self.ledger_file, 'r') as f:
            lines = f.readlines()
            if lines:
                try:
                    last_entry = json.loads(lines[-1])
                    self.last_hash = last_entry.get("hash", self.last_hash)
                except json.JSONDecodeError:
                    logger.error("Security: Audit Ledger corrupted! Could not decode last line.")

    def record_event(self, event_type: str, actor: str, payload: dict):
        """
        Records an event to the ledger.
        """
        timestamp = time.time()
        
        # Canonicalize payload for hashing consistency
        payload_str = json.dumps(payload, sort_keys=True)
        
        # Create hash chain
        entry_content = f"{self.last_hash}|{timestamp}|{event_type}|{actor}|{payload_str}"
        entry_hash = hashlib.sha256(entry_content.encode('utf-8')).hexdigest()
        
        record = {
            "prev_hash": self.last_hash,
            "ts": timestamp,
            "type": event_type,
            "actor": actor,
            "payload": payload,
            "hash": entry_hash
        }
        
        with self.lock:
            with open(self.ledger_file, 'a') as f:
                f.write(json.dumps(record) + "\n")
            self.last_hash = entry_hash
            
        logger.info(f"AUDIT ({event_type}): {actor} - {entry_hash[:8]}...")

    def verify_chain(self) -> bool:
        """
        Verifies the integrity of the blockchain-like ledger from disk.
        """
        try:
            with open(self.ledger_file, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return True

            previous_hash = "GENESIS_HASH_0000000000000000"
            
            for i, line in enumerate(lines):
                if not line.strip(): continue
                try:
                    record = json.loads(line)
                    
                    # 1. Check Previous Hash Link
                    if record["prev_hash"] != previous_hash:
                         logger.critical(f"Ledger Integrity Error at line {i+1}: Previous Hash Mismatch. Expected {previous_hash}, got {record['prev_hash']}")
                         return False

                    # 2. Re-calculate Current Hash
                    # entry_content = f"{self.last_hash}|{timestamp}|{event_type}|{actor}|{payload_str}"
                    # Note: We must replicate EXACTLY what record_event does.
                    payload_str = json.dumps(record["payload"], sort_keys=True)
                    entry_content = f"{record['prev_hash']}|{record['ts']}|{record['type']}|{record['actor']}|{payload_str}"
                    recalc_hash = hashlib.sha256(entry_content.encode('utf-8')).hexdigest()
                    
                    if recalc_hash != record["hash"]:
                        logger.critical(f"Ledger Integrity Error at line {i+1}: Content Hash Mismatch. Recalc {recalc_hash} != {record['hash']}")
                        return False
                    
                    previous_hash = record["hash"]
                    
                except json.JSONDecodeError:
                    return False
            
            return True
        except FileNotFoundError:
            return True # Empty ledger is valid
        except Exception as e:
            logger.error(f"Audit Verify Failed: {e}")
            return False

# Global Instance
audit_ledger = AuditLedger()
