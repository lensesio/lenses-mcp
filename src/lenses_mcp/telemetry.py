"""OpenTelemetry bootstrap.

FastMCP 4 ships native OpenTelemetry instrumentation built against
``opentelemetry-api`` only. It emits a SERVER span per MCP request --
``tools/call <name>``, ``tools/list``, ``prompts/get <name>`` -- carrying the
tool or prompt name, the MCP session id, the negotiated protocol version, and
error status on failure. Those spans go nowhere until an SDK and an exporter
are configured in the process. This module does that, and nothing else.

Configuration is read from ``config`` (see the OpenTelemetry section there).
Tracing is off by default and costs nothing until ``OTEL_ENABLED`` is set.

``setup_telemetry`` never raises: a misconfigured exporter or an unreachable
collector must not stop the MCP server from serving requests. Every failure
path logs and returns ``False``.

Note on ordering: the FastMCP docs suggest configuring the SDK *before*
importing FastMCP. That is not required. OpenTelemetry's API hands out a
``ProxyTracer`` that resolves to the real provider whenever one is installed,
so calling this after the imports works and keeps the import block clean.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from config import (
    OTEL_ENABLED,
    OTEL_EXPORTER,
    OTEL_EXPORTER_OTLP_PROTOCOL,
    OTEL_SERVICE_NAME,
)
from loguru import logger

if TYPE_CHECKING:  # pragma: no cover - import cycle only matters to type checkers
    from opentelemetry.sdk.trace.export import SpanExporter

logger = logger.bind(name="Telemetry")


def _build_span_exporter() -> SpanExporter | None:
    """Build the configured span exporter, or ``None`` if it is unavailable."""
    if OTEL_EXPORTER == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        # stderr, not the ConsoleSpanExporter default of stdout. Under the stdio
        # transport, stdout carries the JSON-RPC wire, and span JSON interleaved
        # with protocol frames breaks the client.
        #
        # The MCP SDK does currently protect against this at the file-descriptor
        # level -- mcp.server.stdio points fd 1 at a dup of fd 2 for the duration
        # of a session and moves the real wire to a private fd -- so writing to
        # stdout happens to be survivable today. That is an implementation detail
        # of another library, with its own failure paths, and it is not something
        # to stake protocol integrity on. Diagnostics belong on stderr regardless;
        # loguru already writes there.
        logger.info("OpenTelemetry exporter: console (stderr)")
        return ConsoleSpanExporter(out=sys.stderr)

    if OTEL_EXPORTER != "otlp":
        logger.warning(
            "Unknown OTEL_EXPORTER '{}'; expected 'otlp' or 'console'. Tracing disabled.",
            OTEL_EXPORTER,
        )
        return None

    if OTEL_EXPORTER_OTLP_PROTOCOL.startswith("grpc"):
        # gRPC is not a runtime dependency -- it pulls grpcio and adds ~27MB to
        # the image. Install the `otlp-grpc` extra to use it.
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        except ImportError:
            logger.warning(
                "OTEL_EXPORTER_OTLP_PROTOCOL=grpc but the gRPC exporter is not installed. "
                "Install the 'otlp-grpc' extra, or use the default http/protobuf on port 4318. "
                "Tracing disabled."
            )
            return None
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[assignment]
            OTLPSpanExporter,
        )

    # No endpoint argument: the SDK resolves OTEL_EXPORTER_OTLP_ENDPOINT (and
    # the per-signal override) itself. For HTTP that means appending /v1/traces
    # to the base URL, which passing endpoint= would skip -- spans then POST to
    # the collector root and are silently dropped.
    exporter = OTLPSpanExporter()
    logger.info(
        "OpenTelemetry exporter: OTLP {} -> {}",
        OTEL_EXPORTER_OTLP_PROTOCOL,
        getattr(exporter, "_endpoint", "(SDK default)"),
    )
    return exporter


def setup_telemetry() -> bool:
    """Install a tracer provider so FastMCP's instrumentation exports spans.

    Returns:
        ``True`` if a tracer provider was installed, ``False`` otherwise.
        Never raises.
    """
    if not OTEL_ENABLED:
        logger.debug("OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = _build_span_exporter()
        if exporter is None:
            return False

        # OTEL_RESOURCE_ATTRIBUTES and OTEL_SERVICE_NAME are merged in by
        # Resource.create(); the explicit service.name here is the fallback.
        provider = TracerProvider(resource=Resource.create({"service.name": OTEL_SERVICE_NAME}))
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except ImportError as exc:
        logger.warning(
            "OTEL_ENABLED=true but the OpenTelemetry SDK is unavailable ({}). Tracing disabled.",
            exc,
        )
        return False
    except Exception as exc:
        # Deliberately broad: telemetry must never break the server.
        logger.warning("OpenTelemetry setup failed ({}). Tracing disabled.", exc)
        return False

    logger.info("OpenTelemetry tracing enabled for service '{}'", OTEL_SERVICE_NAME)
    return True
