import time
from typing import Dict
from asr_trading.core.logger import logger
from asr_trading.core.avionics import telemetry

class MonitoringAgent:
    """
    Collects system-wide metrics and exposes them for scraping.
    """
    def __init__(self):
        self.start_time = time.time()
        self.metrics_buffer = {}

    def get_system_health(self) -> Dict[str, str]:
        """
        Returns high-level health status for dashboard.
        """
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": f"{uptime:.2f}",
            "status": "HEALTHY", # In real impl, check avionics_monitor
            "version": "vNext_Phase7"
        }

    def record_latency(self, component: str, duration_ms: float):
        """
        Records latency for SLO tracking.
        """
        telemetry.record_metric("latency_ms", duration_ms, {"component": component})
        logger.debug(f"MONITOR: {component} latency {duration_ms}ms")
    
    def export_metrics_prometheus(self) -> str:
        """
        Simulates a /metrics endpoint output.
        """
        # Read from telemetry or memory
        # Stub
        output = []
        output.append("# HELP asr_uptime_seconds System Uptime")
        output.append("# TYPE asr_uptime_seconds gauge")
        output.append(f"asr_uptime_seconds {time.time() - self.start_time}")
        return "\n".join(output)

monitoring_agent = MonitoringAgent()
