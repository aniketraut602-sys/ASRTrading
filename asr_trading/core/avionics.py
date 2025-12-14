import time
import functools
import json
import threading
from typing import Dict, Any, Callable
from enum import Enum
from asr_trading.core.logger import logger

class ServiceStatus(Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class Telemetry:
    """
    Centralized metrics recorder.
    In vNext, this would push to Prometheus/Grafana.
    For now, it logs structured JSON to a dedicated metrics file which can be ingested later.
    """
    def __init__(self, log_path="metrics.jsonl"):
        self.lock = threading.Lock()
        self.log_path = log_path
        # Ensure file exists
        with open(self.log_path, 'a') as f:
            pass

    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        if tags is None:
            tags = {}
        
        entry = {
            "ts": time.time(),
            "name": name,
            "value": value,
            "tags": tags
        }
        
        # In a high-perf scenario, this would be async/batched.
        with self.lock:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + "\n")

    def record_event(self, event_type: str, details: Dict[str, Any]):
        self.record_metric(f"event.{event_type}", 1.0, details)

telemetry = Telemetry()

class HealthMonitor:
    """
    Tracks the heartbeat of all registered services.
    Services must call `heartbeat(service_name)` periodically.
    """
    def __init__(self):
        self._services: Dict[str, float] = {}
        self._thresholds: Dict[str, float] = {}
        self._lock = threading.Lock()

    def register_service(self, name: str, timeout_seconds: float = 60.0):
        with self._lock:
            self._services[name] = time.time()
            self._thresholds[name] = timeout_seconds
            logger.info(f"Avionics: Service '{name}' registered with {timeout_seconds}s heartbeat.")

    def heartbeat(self, name: str):
        with self._lock:
            if name in self._services:
                self._services[name] = time.time()

    def check_health(self) -> Dict[str, ServiceStatus]:
        status_map = {}
        now = time.time()
        with self._lock:
            for name, last_beat in self._services.items():
                elapsed = now - last_beat
                threshold = self._thresholds.get(name, 60.0)
                
                if elapsed > threshold * 2:
                    status_map[name] = ServiceStatus.CRITICAL
                    telemetry.record_event("health_check_critical", {"service": name, "elapsed": elapsed})
                elif elapsed > threshold:
                    status_map[name] = ServiceStatus.DEGRADED
                    telemetry.record_event("health_check_degraded", {"service": name, "elapsed": elapsed})
                else:
                    status_map[name] = ServiceStatus.OK
        
        return status_map

avionics_monitor = HealthMonitor()

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """
    Protects the system from failing external services.
    If `failure_threshold` errors occur within `recovery_timeout`, the breaker opens.
    """
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def _allow_request(self) -> bool:
        with self._lock:
            if self.state == "OPEN":
                now = time.time()
                if now - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info(f"CircuitBreaker '{self.name}' entering HALF_OPEN state.")
                    return True
                return False
            return True

    def _on_success(self):
        with self._lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logger.info(f"CircuitBreaker '{self.name}' CLOSED (Recovered).")
            elif self.state == "CLOSED":
                self.failures = 0

    def _on_failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            telemetry.record_metric("circuit_breaker.failure", 1, {"name": self.name})
            
            if self.state == "HALF_OPEN":
                self.state = "OPEN"
                logger.error(f"CircuitBreaker '{self.name}' Re-OPENED (Check failed).")
                
            elif self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"CircuitBreaker '{self.name}' OPENED (Failures: {self.failures}).")
                telemetry.record_event("circuit_breaker_opened", {"name": self.name})

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self._allow_request():
                raise CircuitBreakerOpenException(f"CircuitBreaker '{self.name}' is OPEN.")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e # Re-raise for caller to handle
        return wrapper

