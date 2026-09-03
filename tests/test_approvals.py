"""Tests for the governance approval-request MCP tools — payload shape against Lenses API.

These tests pin the wire shape of the agent's /api/v1/approvals endpoints as
proxied through HQ. The two easiest things to silently break are the
`"type": "CreateNewEntity"` discriminator (circe rejects the body without it)
and the `pageSize` query param (required by the agent, no server default).

Every server built here sets ``mask_error_details=True`` to match production
(``server.py``). Without it a tool could raise a bare ``ValueError`` and these
tests would still see its message, while the model in production would only
ever get "Error calling tool" — so the validation messages have to be
``ToolError`` to survive, and asserting on them only means something under
masking.
"""

import json
import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

import httpx2
import pytest
from fastmcp import Client, FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

import clients.http_client as http_client_module
from tools.approvals import register_approvals
from tools.topics import register_topics


@contextmanager
def _capturing_transport(status_code: int = 200, body: dict | None = None):
    """Replace the shared async client with a mock that records every request.

    Yields the list of captured `httpx2.Request`s so tests can assert on
    method, URL and body without involving a real Lenses instance.
    """
    captured: list[httpx2.Request] = []
    response_body = body if body is not None else {"success": True}

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(status_code, json=response_body)

    transport = httpx2.MockTransport(handler)
    original = http_client_module._async_client
    http_client_module._async_client = httpx2.AsyncClient(transport=transport)
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
    """Fresh FastMCP server with only the approval tools registered."""
    mcp = FastMCP(name="test-approvals", mask_error_details=True)
    register_approvals(mcp)
    return mcp


async def _call_tool(mcp: FastMCP, name: str, args: dict):
    async with Client(mcp) as client:
        return await client.call_tool(name, args)


# ---------------------------------------------------------------------------
# request_topic_creation — body must be a CreateNewEntity with the `type`
# discriminator, matching the agent's NewRequest codec.
# ---------------------------------------------------------------------------


async def test_request_topic_creation_sends_create_new_entity_body(mcp_server):
    with _capturing_transport(body={"id": "6a1f0e9c-0000-0000-0000-000000000000"}) as captured:
        await _call_tool(
            mcp_server,
            "request_topic_creation",
            {
                "environment": "dev",
                "topic_name": "topic-invoices",
                "reason": "Invoice records from billing app Foo",
                "partitions": 5,
                "replication": 2,
                "configs": {"delete.retention.ms": "30000"},
                "tags": ["billing", "invoices"],
                "records_size": 15,
            },
        )

    assert len(captured) == 1
    request = captured[0]
    assert request.method == "POST"
    assert request.url.path == "/api/v1/environments/dev/proxy/api/v1/approvals"

    body = json.loads(request.content)
    assert body == {
        "type": "CreateNewEntity",
        "entityName": "topic-invoices",
        "entityType": "KafkaTopic",
        "settings": {
            "replication": 2,
            "partitions": 5,
            "topicConfig": {"delete.retention.ms": "30000"},
            "capacity": {"recordsSize": 15, "dataProducedPerDay": None, "consumers": None},
        },
        "metadata": {"reason": "Invoice records from billing app Foo", "tags": ["billing", "invoices"]},
    }


async def test_request_topic_creation_omits_topic_config_when_absent(mcp_server):
    """No `configs` -> no topicConfig key (agent treats a missing key as None)."""
    with _capturing_transport(body={"id": "x"}) as captured:
        await _call_tool(
            mcp_server,
            "request_topic_creation",
            {"environment": "dev", "topic_name": "t1", "reason": "because"},
        )

    body = json.loads(captured[0].content)
    assert "topicConfig" not in body["settings"]
    assert body["settings"]["replication"] == 1
    assert body["settings"]["partitions"] == 1
    assert body["metadata"] == {"reason": "because", "tags": []}


async def test_request_topic_creation_wraps_validation_errors(mcp_server):
    """Agent-side 400s (topic exists, bad replication) reach the model verbatim.

    The message only survives because the tool raises ToolError; under
    mask_error_details any other exception would arrive as "Error calling tool".
    """
    with (
        _capturing_transport(status_code=400, body={"title": "Topic t1 already exists"}),
        pytest.raises(Exception, match=r"Topic creation request failed: .*Topic t1 already exists"),
    ):
        await _call_tool(
            mcp_server,
            "request_topic_creation",
            {"environment": "dev", "topic_name": "t1", "reason": "because"},
        )


# ---------------------------------------------------------------------------
# list_approval_requests — pageSize is required by the agent; approvalStatus
# is repeatable.
# ---------------------------------------------------------------------------


async def test_list_requests_always_sends_page_size(mcp_server):
    with _capturing_transport(body={"values": [], "pagesAmount": 0, "totalCount": 0}) as captured:
        await _call_tool(mcp_server, "list_approval_requests", {"environment": "dev"})

    request = captured[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/environments/dev/proxy/api/v1/approvals"
    params = dict(request.url.params)
    assert params["pageSize"] == "25"
    assert params["page"] == "1"


async def test_list_requests_repeats_approval_status_param(mcp_server):
    with _capturing_transport(body={"values": [], "pagesAmount": 0, "totalCount": 0}) as captured:
        await _call_tool(
            mcp_server,
            "list_approval_requests",
            {
                "environment": "dev",
                "statuses": ["Pending", "Rejected"],
                "entity_name": "invoices",
                "page": 2,
                "page_size": 10,
                "sort_field": "createdAt",
                "sort_order": "desc",
            },
        )

    url = captured[0].url
    assert url.params.get_list("approvalStatus") == ["Pending", "Rejected"]
    assert url.params["entityName"] == "invoices"
    assert url.params["page"] == "2"
    assert url.params["pageSize"] == "10"
    assert url.params["sortField"] == "createdAt"
    assert url.params["sortOrder"] == "desc"


async def test_list_requests_encodes_entity_name(mcp_server):
    """A model-supplied filter must not be able to inject query parameters.

    httpx2 percent-encodes spaces in a raw query string but leaves "&" and "="
    untouched, so building the query with f-strings would let `entity_name`
    smuggle in extra parameters (here, a second page size).
    """
    with _capturing_transport(body={"values": [], "pagesAmount": 0, "totalCount": 0}) as captured:
        await _call_tool(
            mcp_server,
            "list_approval_requests",
            {"environment": "dev", "entity_name": "a&pageSize=9999"},
        )

    url = captured[0].url
    assert url.params.get_list("entityName") == ["a&pageSize=9999"]
    assert url.params.get_list("pageSize") == ["25"]
    assert "%26" in str(url)


async def test_list_requests_rejects_invalid_status(mcp_server):
    with _capturing_transport() as captured, pytest.raises(Exception, match="Invalid statuses"):
        await _call_tool(
            mcp_server,
            "list_approval_requests",
            {"environment": "dev", "statuses": ["pending"]},  # case-sensitive
        )
    assert captured == []


async def test_list_requests_rejects_invalid_sort_field(mcp_server):
    with _capturing_transport() as captured, pytest.raises(Exception, match="sort_field"):
        await _call_tool(
            mcp_server,
            "list_approval_requests",
            {"environment": "dev", "sort_field": "reviewedAt"},
        )
    assert captured == []


# ---------------------------------------------------------------------------
# get_approval_request
# ---------------------------------------------------------------------------


async def test_get_request_hits_detail_endpoint(mcp_server):
    request_id = "6a1f0e9c-0000-0000-0000-000000000000"
    with _capturing_transport(body={"id": request_id, "approvalStatus": "Pending"}) as captured:
        await _call_tool(
            mcp_server,
            "get_approval_request",
            {"environment": "dev", "request_id": request_id},
        )

    request = captured[0]
    assert request.method == "GET"
    assert request.url.path == f"/api/v1/environments/dev/proxy/api/v1/approvals/{request_id}"


async def test_get_request_rejects_non_uuid_id(mcp_server):
    """request_id is interpolated into the path, and httpx2 resolves dot segments.

    Without the guard, "../../environments" would leave the approvals endpoint
    entirely and hit another HQ path with the server's own credentials.
    """
    with _capturing_transport() as captured, pytest.raises(Exception, match="must be a UUID"):
        await _call_tool(
            mcp_server,
            "get_approval_request",
            {"environment": "dev", "request_id": "../../../api/v1/users"},
        )
    assert captured == []


# ---------------------------------------------------------------------------
# create_topic — a 403 (missing kafka:CreateTopic) points the model at the
# governed request path.
# ---------------------------------------------------------------------------


async def test_create_topic_403_suggests_governed_path():
    """The redirect keys off the HTTP status, not the wording of HQ's error body.

    The body here deliberately contains neither "403" nor "forbidden": matching
    on the message would miss this, and HQ owns that wording, not us.
    """
    mcp = FastMCP(name="test-topics-hint", mask_error_details=True)
    register_topics(mcp)
    with (
        _capturing_transport(status_code=403, body={"title": "User lacks permission to create topics"}),
        pytest.raises(Exception, match="request_topic_creation"),
    ):
        await _call_tool(
            mcp,
            "create_topic",
            {"environment": "dev", "topic_name": "t1"},
        )


async def test_create_topic_non_403_has_no_hint():
    """A 400 is a real failure, not a permissions problem — no governed-path nudge."""
    mcp = FastMCP(name="test-topics-no-hint", mask_error_details=True)
    register_topics(mcp)
    with (
        _capturing_transport(status_code=400, body={"title": "Invalid replication factor"}),
        pytest.raises(Exception, match="Invalid replication factor") as excinfo,
    ):
        await _call_tool(
            mcp,
            "create_topic",
            {"environment": "dev", "topic_name": "t1"},
        )
    assert "request_topic_creation" not in str(excinfo.value)
