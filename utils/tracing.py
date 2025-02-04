from opentelemetry import trace
from opentelemetry.trace import Tracer

tracer: Tracer = trace.get_tracer(__name__) 