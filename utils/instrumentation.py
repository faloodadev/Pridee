from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from pyinstrument import Profiler
from dask.distributed import Client as DaskClient
import functools
from utils.logger import log

tracer = trace.get_tracer(__name__)

def setup_telemetry(endpoint: str = "http://localhost:4317") -> None:
    """Initialize OpenTelemetry tracing."""
    trace.set_tracer_provider(TracerProvider())
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    log.info("Telemetry initialized")

def trace_method(name: str = None):
    """Decorator to trace method execution"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name or func.__name__) as span:
                span.set_attribute("function.name", func.__name__)
                return await func(*args, **kwargs)
        return wrapper
    return decorator

class BotInstrumentation:
    def __init__(self):
        self.profiler = Profiler()
        self.dask_client = None

    async def setup(self):
        """Initialize instrumentation"""
        self.dask_client = await DaskClient(asynchronous=True)
        self.profiler.start()

    async def cleanup(self):
        """Cleanup instrumentation"""
        self.profiler.stop()
        self.profiler.write_html("profile_results.html")
        if self.dask_client:
            await self.dask_client.close() 