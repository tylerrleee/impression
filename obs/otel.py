"""
OpenTelemetry bootstrap

Call init_telemetry("web") or "worker" at process start time
Then create spans and record metrics
- Metric: across all jobs, what is the rate and distribution of pass and failures
- Span: An instance of Tracers that tracks the performance and how long each step between resources take


"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

# Guard against double init (e.g. uvicorn --reload importing the app twice)
_initialized = False

def init_telemetry(service_name: str) -> None:
    """ Wire global tracer + meter providers for process
    Idempotent. Load once    
    """
    global _initialized
    if _initialized:
        return
    _initialized = True
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not endpoint:
        # No-op mode: leave default no-op provider in place
        return

    resource = Resource.create(
        {
            "service.name" : service_name,
            "service.namespace" : "impression",
        }
    )

    # TRACES
    # BatchSpanProcesser buffers spans and ships them on a backgrund thread
    # hence exporting doesn't sit in request path

    tracer_provider = TracerProvider(resource = resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # METRICS
    # Periodic Exporting Metric Reader push current metric value on an interval

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
    )
    meter_provider = MeterProvider(resource       = resource,
                                   metric_readers = [metric_reader])
    metrics.set_meter_provider(meter_provider)