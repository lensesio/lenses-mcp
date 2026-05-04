"""Tests for the Kafka consumer-group MCP tools — payload shape against Lenses API.

These tests pin the wire shape of the bulk-offset endpoints so future refactors
can't silently drift back to a list-of-tuples body, which the Lenses API
rejects (the endpoints expect a single object per the OpenAPI spec).
"""

import json
import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

import httpx
import pytest
from fastmcp import Client, FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

import clients.http_client as http_client_module
from tools.kafka_consumer_groups import register_kafka_consumer_groups


@contextmanager
def _capturing_transport(status_code: int = 200, body: dict | None = None):
    """Replace the shared async client with a mock that records every request.

    Yields the list of captured `httpx.Request`s so tests can assert on
    method, URL and body without involving a real Lenses instance.
    """
    captured: list[httpx.Request] = []
    response_body = body if body is not None else {"success": True}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code, json=response_body)

    transport = httpx.MockTransport(handler)
    original = http_client_module._async_client
    http_client_module._async_client = httpx.AsyncClient(transport=transport)
    try:
        yield captured
    finally:
        http_client_module._async_client = original


@pytest.fixture(autouse=True)
def _stub_resolve_token():
    """Provide a deterministic token without depending on OAuth context or env vars."""
    with patch("clients.http_client.resolve_token", return_value="test-token"):
        yield


@pytest.fixture
def mcp_server() -> FastMCP:
    """Fresh FastMCP server with only the consumer-group tools registered."""
    mcp = FastMCP(name="test-kafka-consumer-groups")
    register_kafka_consumer_groups(mcp)
    return mcp


async def _call_tool(mcp: FastMCP, name: str, args: dict):
    async with Client(mcp) as client:
        return await client.call_tool(name, args)


# ---------------------------------------------------------------------------
# update_consumer_group_offsets — body must be a single object with `type`
# and `topics`, matching agent_BulkPartitionOffsetRequest.
# ---------------------------------------------------------------------------


async def test_update_offsets_reset_to_start_sends_object_body(mcp_server):
    """`reset_to="start"` posts {"type": "start", "topics": [...]} with no `target`."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "update_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["topic-a", "topic-b"],
                "reset_to": "start",
            },
        )

    assert len(captured) == 1
    req = captured[0]
    assert req.method == "PUT"
    assert req.url.path == "/api/v1/environments/demo/proxy/api/consumers/g1/offsets"

    body = json.loads(req.content)
    assert body == {"type": "start", "topics": ["topic-a", "topic-b"]}


async def test_update_offsets_reset_to_end_omits_target(mcp_server):
    """`reset_to="end"` posts {"type": "end", "topics": [...]} and never adds `target`."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "update_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["topic-a"],
                "reset_to": "end",
            },
        )

    body = json.loads(captured[0].content)
    assert body == {"type": "end", "topics": ["topic-a"]}
    assert "target" not in body, "`target` must only appear for reset_to='timestamp'"


async def test_update_offsets_reset_to_timestamp_includes_target(mcp_server):
    """`reset_to="timestamp"` posts the discriminator plus the RFC 3339 `target`."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "update_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["topic-a"],
                "reset_to": "timestamp",
                "target": "2026-04-28T10:00:00Z",
            },
        )

    body = json.loads(captured[0].content)
    assert body == {
        "type": "timestamp",
        "topics": ["topic-a"],
        "target": "2026-04-28T10:00:00Z",
    }


async def test_update_offsets_timestamp_without_target_does_not_call_api(mcp_server):
    """A missing `target` for the timestamp variant fails before any HTTP call.

    This is a client-side guard: hitting the Lenses API with a timestamp body
    minus `target` would 400, and we'd rather fail loudly with a clear message.
    """
    from fastmcp.exceptions import ToolError

    with _capturing_transport() as captured, pytest.raises(ToolError, match="target"):
        await _call_tool(
            mcp_server,
            "update_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["topic-a"],
                "reset_to": "timestamp",
            },
        )

    assert captured == [], "No HTTP request should have been issued"


async def test_update_offsets_url_encodes_path_segments(mcp_server):
    """URL path is built from `environment` and `group_id` — no extra encoding asserted,
    just that the segments end up where Lenses expects them."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "update_consumer_group_offsets",
            {
                "environment": "prod",
                "group_id": "my-group",
                "topics": ["t"],
                "reset_to": "start",
            },
        )

    assert captured[0].url.path == "/api/v1/environments/prod/proxy/api/consumers/my-group/offsets"


# ---------------------------------------------------------------------------
# delete_consumer_group_offsets — body must be {"topics": [...]}, matching
# agent_BulkPartitionOffsetDeleteRequest.
# ---------------------------------------------------------------------------


async def test_delete_offsets_sends_topics_object_body(mcp_server):
    """`delete_consumer_group_offsets` posts {"topics": [...]}, not a list of tuples."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "delete_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["topic-a", "topic-b"],
            },
        )

    assert len(captured) == 1
    req = captured[0]
    assert req.method == "POST"
    assert req.url.path == "/api/v1/environments/demo/proxy/api/consumers/g1/offsets/delete"

    body = json.loads(req.content)
    assert body == {"topics": ["topic-a", "topic-b"]}


async def test_delete_offsets_single_topic(mcp_server):
    """Single-topic case still wraps the topic in a list under `topics`."""
    with _capturing_transport() as captured:
        await _call_tool(
            mcp_server,
            "delete_consumer_group_offsets",
            {
                "environment": "demo",
                "group_id": "g1",
                "topics": ["only-one"],
            },
        )

    body = json.loads(captured[0].content)
    assert body == {"topics": ["only-one"]}
    assert isinstance(body["topics"], list)
