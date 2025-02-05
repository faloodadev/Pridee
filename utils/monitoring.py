from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
import logging
from pyinstrument import Profiler
from typing import Optional, Dict
from collections import defaultdict
import time
import functools
import config
from utils.logger import log

logging.getLogger('opentelemetry').setLevel(logging.ERROR)
logging.getLogger('distributed').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

class PerformanceMonitoring:
    def __init__(self):
        self.profiler: Optional[Profiler] = None
        self.tracer = trace.get_tracer(__name__)
        self.stats = defaultdict(lambda: {
            'calls': 0,
            'errors': 0,
            'total_time': 0
        })
        self._last_cleanup = time.time()
        log.info("Performance monitoring initialized")

    def setup(self, otlp_endpoint: str = None, **kwargs):
        """Setup monitoring with optional OTLP endpoint."""
        try:
            log.info("Monitoring setup complete")
        except Exception as e:
            log.error(f"Failed to setup monitoring: {e}")

    def cleanup(self):
        """Cleanup monitoring systems"""
        if self.profiler:
            self.profiler.stop()
            self.profiler.write_html("profile_results.html")

    def trace_method(self, func):
        """Decorator to trace method execution."""
        async def wrapper(*args, **kwargs):
            with self.tracer.start_as_current_span(func.__name__) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        return wrapper

    def record_operation(self, name: str, duration: float, error: bool = False):
        """Record an operation's duration and status."""
        with self.tracer.start_as_current_span(name) as span:
            span.set_attribute("duration", duration)
            span.set_attribute("error", error)

    def get_stats(self) -> Dict:
        """Get current statistics"""
        return dict(self.stats)

    def shutdown(self):
        """Cleanup monitoring resources."""
        pass

monitoring = PerformanceMonitoring()

def setup_monitoring():
    """Setup monitoring with OpenTelemetry."""
    resource = Resource.create({
        "service.name": "evict.bot",
        "service.version": "1.0.0"
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    return provider

def cleanup_monitoring():
    """Cleanup monitoring systems"""
    try:
        monitoring.cleanup()
        log.info("Monitoring cleanup complete")
    except Exception as e:
        log.warning(f"Failed to cleanup monitoring: {e}")

__all__ = ['monitoring', 'setup_monitoring', 'cleanup_monitoring'] 