from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from pyinstrument import Profiler
import logging
from typing import Optional, Dict
from collections import defaultdict
import time
import functools

log = logging.getLogger(__name__)

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

    def setup(self, otlp_endpoint: str = "http://localhost:4317"):
        """Initialize monitoring systems"""
        provider = TracerProvider()
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self.profiler = Profiler()
        self.profiler.start()
        log.info("Monitoring initialized")

    def cleanup(self):
        """Cleanup monitoring systems"""
        if self.profiler:
            self.profiler.stop()
            self.profiler.write_html("profile_results.html")

    def trace_method(self, name: str = None):
        """Decorator to trace method execution"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(name or func.__name__) as span:
                    span.set_attribute("function.name", func.__name__)
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        self.record_operation(func.__name__, time.time() - start_time)
                        return result
                    except Exception as e:
                        self.record_operation(func.__name__, time.time() - start_time, error=True)
                        raise
            return wrapper
        return decorator

    def record_operation(self, operation: str, duration: float, error: bool = False):
        """Record operation statistics"""
        self.stats[operation]['calls'] += 1
        self.stats[operation]['total_time'] += duration
        if error:
            self.stats[operation]['errors'] += 1

        if time.time() - self._last_cleanup > 3600:
            self.stats.clear()
            self._last_cleanup = time.time()

    def get_stats(self) -> Dict:
        """Get current statistics"""
        return dict(self.stats) 