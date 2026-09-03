"""Tests for the OpenTelemetry bootstrap.

Two layers here:

* ``TestSetupTelemetry`` covers the configuration handling in isolation, with
  ``config`` values monkeypatched on the ``telemetry`` module. These assert the
  contract that matters most in production: telemetry is off unless asked for,
  and no misconfiguration is ever fatal.

* ``TestSpanEmission`` is the end-to-end check. It installs a real SDK with an
  in-memory exporter, drives the real server through a real MCP client, and
  asserts on the spans FastMCP actually produced. That is what proves the
  instrumentation is wired up, rather than merely that our code runs.

The tracer provider is process-global and can only be set once, so the
span-emission tests install it lazily and share it.
"""

from __future__ import annotations

import os
import sys

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

import server
import telemetry
from fastmcp import Client

_EXPORTER: InMemorySpanExporter | None = None


def _install_provider() -> InMemorySpanExporter:
    """Install a global tracer provider once, returning its in-memory exporter."""
    global _EXPORTER
    if _EXPORTER is None:
        _EXPORTER = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
        trace.set_tracer_provider(provider)
    return _EXPORTER


@pytest.fixture
def spans() -> InMemorySpanExporter:
    exporter = _install_provider()
    exporter.clear()
    return exporter


class TestSetupTelemetry:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(telemetry, "OTEL_ENABLED", False)
        assert telemetry.setup_telemetry() is False

    def test_unknown_exporter_is_not_fatal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bad exporter name must never stop the server from starting."""
        monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "nonsense")
        assert telemetry.setup_telemetry() is False

    def test_console_exporter_builds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "console")
        assert isinstance(telemetry._build_span_exporter(), ConsoleSpanExporter)

    def test_console_exporter_writes_to_stderr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Never stdout: under the stdio transport that is the JSON-RPC wire.

        ConsoleSpanExporter defaults to stdout. Span JSON interleaved with
        protocol frames breaks the client, so the exporter must be pointed at
        stderr explicitly rather than relying on the MCP SDK's fd-level stdout
        diversion to save us.
        """
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "console")
        exporter = telemetry._build_span_exporter()
        assert exporter.out is sys.stderr
        assert exporter.out is not sys.stdout

    def test_otlp_http_exporter_is_the_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "otlp")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
        assert isinstance(telemetry._build_span_exporter(), OTLPSpanExporter)

    def test_http_exporter_appends_the_traces_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OTEL_EXPORTER_OTLP_ENDPOINT is a base URL; /v1/traces must be appended.

        Regression test. Passing ``endpoint=`` to the HTTP exporter ourselves
        skips that append, so spans POST to the collector root and are dropped
        silently -- the server logs "tracing enabled" and nothing ever arrives.
        Deferring to the SDK is what makes the spec'd semantics apply.
        """
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "otlp")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

        exporter = telemetry._build_span_exporter()
        assert exporter._endpoint == "http://collector:4318/v1/traces"

    def test_traces_endpoint_override_is_used_verbatim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The per-signal override is a full URL and must not be rewritten."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://collector:4318/custom/path")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "otlp")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

        exporter = telemetry._build_span_exporter()
        assert exporter._endpoint == "http://collector:4318/custom/path"

    def test_grpc_without_the_extra_is_not_fatal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """gRPC is an optional extra; asking for it without it must degrade, not crash."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if "otlp.proto.grpc" in name:
                raise ImportError("no grpc exporter")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(telemetry, "OTEL_EXPORTER", "otlp")
        monkeypatch.setattr(telemetry, "OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
        monkeypatch.setattr(builtins, "__import__", fake_import)
        assert telemetry._build_span_exporter() is None

    def test_exporter_failure_is_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Telemetry must never take the server down, whatever goes wrong."""
        monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)

        def boom() -> None:
            raise RuntimeError("exporter exploded")

        monkeypatch.setattr(telemetry, "_build_span_exporter", boom)
        assert telemetry.setup_telemetry() is False


class TestSpanEmission:
    """FastMCP's instrumentation, exercised through a real client."""

    @staticmethod
    def _server_spans(exporter: InMemorySpanExporter) -> dict[str, object]:
        return {s.name: s for s in exporter.get_finished_spans() if s.kind is SpanKind.SERVER}

    async def test_tool_call_emits_a_span_named_after_the_tool(self, spans: InMemorySpanExporter) -> None:
        async with Client(server.mcp) as client:
            await client.call_tool("list_environments", {}, raise_on_error=False)

        span = self._server_spans(spans).get("tools/call list_environments")
        assert span is not None, f"got: {sorted(self._server_spans(spans))}"
        assert span.attributes["gen_ai.tool.name"] == "list_environments"
        assert span.attributes["mcp.method.name"] == "tools/call"
        assert span.attributes["fastmcp.server.name"] == "Lenses.io"

    async def test_tools_list_emits_a_span(self, spans: InMemorySpanExporter) -> None:
        async with Client(server.mcp) as client:
            await client.list_tools()

        assert "tools/list" in self._server_spans(spans)

    async def test_failing_tool_call_is_recorded_as_an_error(self, spans: InMemorySpanExporter) -> None:
        """A failed call must still be traced, and marked failed."""
        # No Lenses backend in tests, so this call fails at the HTTP layer.
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_environments", {}, raise_on_error=False)
        assert result.is_error

        span = self._server_spans(spans).get("tools/call list_environments")
        assert span is not None
        assert span.status.status_code is StatusCode.ERROR
