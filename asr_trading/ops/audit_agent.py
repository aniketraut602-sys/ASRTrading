from asr_trading.core.security import audit_ledger
from asr_trading.core.logger import logger

class AuditAgent:
    """
    Guardian of the Immutable Ledger.
    """
    def run_integrity_check(self) -> bool:
        """
        Re-calculates hashes of the ledger to ensure no tampering.
        """
        logger.info("AUDIT: Starting Integrity Check...")
        try:
            # We assume audit_ledger exposes the list or a verification method
            # For this Phase, we trust the in-memory verifying of the AuditLedger class if implemented
            # Or we implement a check here if AuditLedger exposed the raw chain.
            
            # Simulated check
            is_valid = audit_ledger.verify_chain() # Assuming we add this to Security/AuditLedger
            
            if is_valid:
                logger.info("AUDIT: Ledger Integrity VERIFIED. All hashes valid.")
                return True
            else:
                logger.critical("AUDIT: LEDGER TAMPERING DETECTED! HASH MISMATCH.")
                return False
        except Exception as e:
            logger.error(f"AUDIT: Verification Failed: {e}")
            return False

    def export_trade_log(self, file_path="trade_audit.csv"):
        logger.info(f"AUDIT: Exporting daily trade log to {file_path}")
        # Stub export
        with open(file_path, "w") as f:
            f.write("timestamp,hash,event,details\n")
            # Loop through ledger and write

audit_agent = AuditAgent()
