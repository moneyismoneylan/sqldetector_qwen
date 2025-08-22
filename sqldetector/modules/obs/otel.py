"""OpenTelemetry helper stub."""
from typing import Any, Optional

try:  # pragma: no cover - optional
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )  # type: ignore
except Exception:  # pragma: no cover
    trace = None  # type: ignore


def get_tracer(mode: str = "off") -> Optional[Any]:
    if trace is None or mode == "off":
        return None
    provider = TracerProvider()
    if mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)
