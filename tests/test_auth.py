"""Tests for DiscoveryTokenVerifier (metadata discovery + RFC 7662) and token resolution."""

import os
import sys
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

from auth import DiscoveryTokenVerifier, resolve_token

AUTH_SERVER = "https://auth.example.com"

METADATA_RESPONSE = {
    "issuer": AUTH_SERVER,
    "introspection_endpoint": f"{AUTH_SERVER}/oauth2/introspect",
    "token_endpoint": f"{AUTH_SERVER}/oauth2/token",
}

ACTIVE_TOKEN_RESPONSE = {
    "active": True,
    "client_id": "test-client",
    "scope": "read write",
    "exp": int(time.time()) + 3600,
    "sub": "user-123",
}


def _build_verifier(
    introspection_url: str | None = None,
    cache_ttl: int | None = None,
) -> DiscoveryTokenVerifier:
    return DiscoveryTokenVerifier(
        auth_server_url=AUTH_SERVER,
        introspection_url=introspection_url,
        cache_ttl_seconds=cache_ttl,
    )


def _mock_transport(
    metadata: dict = METADATA_RESPONSE,
    introspection: dict = ACTIVE_TOKEN_RESPONSE,
    introspection_status: int = 200,
) -> httpx.MockTransport:
    """Return a MockTransport that serves metadata and introspection endpoints."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/oauth-authorization-server":
            return httpx.Response(200, json=metadata)
        if request.url.path == "/oauth2/introspect":
            return httpx.Response(introspection_status, json=introspection)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _patch_client(transport: httpx.MockTransport):
    """Patch httpx.AsyncClient so each ``async with`` block gets a fresh client."""
    _OriginalClient = httpx.AsyncClient
    return patch("auth.httpx.AsyncClient", side_effect=lambda **kw: _OriginalClient(transport=transport))


# ---------------------------------------------------------------------------
# DiscoveryTokenVerifier — construction
# ---------------------------------------------------------------------------


def test_verifier_starts_undiscovered():
    """Discovery has not run and introspection URL is None until first call."""
    v = _build_verifier()
    assert not v._discovered
    assert v._introspection_url is None


def test_verifier_stores_introspection_url_override():
    """Explicit introspection_url skips discovery."""
    v = _build_verifier(introspection_url="https://custom.idp.io/introspect")
    assert v._introspection_url == "https://custom.idp.io/introspect"
    assert v._discovered is True


def test_verifier_strips_trailing_slash():
    """Trailing slash on auth_server_url is stripped."""
    v = DiscoveryTokenVerifier(auth_server_url="https://auth.example.com/")
    assert v._auth_server_url == "https://auth.example.com"


# ---------------------------------------------------------------------------
# _discover — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_sets_introspection_url():
    """After discovery the introspection URL is resolved from metadata."""
    v = _build_verifier()
    transport = _mock_transport()

    with _patch_client(transport):
        await v._discover()

    assert v._discovered is True
    assert v._introspection_url == f"{AUTH_SERVER}/oauth2/introspect"


@pytest.mark.asyncio
async def test_discover_falls_back_to_default_introspection_url():
    """When metadata has no introspection_endpoint, the default path is used."""
    metadata_without_introspection = {"issuer": AUTH_SERVER}
    v = _build_verifier()
    transport = _mock_transport(metadata=metadata_without_introspection)

    with _patch_client(transport):
        await v._discover()

    assert v._introspection_url == f"{AUTH_SERVER}/oauth2/introspect"


# ---------------------------------------------------------------------------
# _discover — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_metadata_failure_raises():
    """If metadata fetch fails, the exception propagates and state is unchanged."""
    v = _build_verifier()

    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(failing_handler)

    with (
        _patch_client(transport),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await v._discover()

    assert not v._discovered


# ---------------------------------------------------------------------------
# verify_token — lazy discovery + introspection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_triggers_discovery():
    """First verify_token call bootstraps discovery before introspecting."""
    v = _build_verifier()
    transport = _mock_transport()

    with _patch_client(transport):
        result = await v.verify_token("some-token")

    assert v._discovered is True
    assert result is not None
    assert result.client_id == "test-client"
    assert set(result.scopes) == {"read", "write"}


@pytest.mark.asyncio
async def test_verify_token_skips_discovery_with_override():
    """When introspection_url is set, discovery is skipped."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect")
    transport = _mock_transport()

    with _patch_client(transport):
        result = await v.verify_token("some-token")

    assert result is not None
    assert result.client_id == "test-client"


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_discovery_failure():
    """If discovery fails, verify_token returns None (reject the token)."""
    v = _build_verifier()
    v._discover = AsyncMock(side_effect=RuntimeError("network down"))

    result = await v.verify_token("some-token")
    assert result is None


@pytest.mark.asyncio
async def test_verify_token_retries_discovery_after_failure():
    """After a failed discovery, the next call retries."""
    v = _build_verifier()
    call_count = 0
    transport = _mock_transport()

    async def flaky_discover() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        v._introspection_url = f"{AUTH_SERVER}/oauth2/introspect"
        v._discovered = True

    v._discover = flaky_discover  # type: ignore[assignment]

    assert await v.verify_token("tok") is None  # first call fails
    assert call_count == 1

    with _patch_client(transport):
        result = await v.verify_token("tok")  # second call retries

    assert call_count == 2
    assert v._discovered is True
    assert result is not None


@pytest.mark.asyncio
async def test_verify_token_inactive_returns_none():
    """An inactive token is rejected."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect")
    transport = _mock_transport(introspection={"active": False})

    with _patch_client(transport):
        result = await v.verify_token("expired-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_expired_returns_none():
    """A token whose exp is in the past is rejected."""
    expired_response = {**ACTIVE_TOKEN_RESPONSE, "exp": int(time.time()) - 3600}
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect")
    transport = _mock_transport(introspection=expired_response)

    with _patch_client(transport):
        result = await v.verify_token("expired-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_http_error_returns_none():
    """Non-200 introspection response is rejected."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect")
    transport = _mock_transport(introspection_status=500)

    with _patch_client(transport):
        result = await v.verify_token("some-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_no_auth_header_sent():
    """The introspection request must NOT contain an Authorization header."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect")
    captured_headers: dict = {}

    def capturing_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/introspect":
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json=ACTIVE_TOKEN_RESPONSE)
        return httpx.Response(404)

    transport = httpx.MockTransport(capturing_handler)

    with _patch_client(transport):
        await v.verify_token("some-token")

    assert "authorization" not in captured_headers


@pytest.mark.asyncio
async def test_verify_token_caching():
    """Cached results are returned without a second introspection call."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect", cache_ttl=300)
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        if request.url.path == "/oauth2/introspect":
            call_count += 1
            return httpx.Response(200, json=ACTIVE_TOKEN_RESPONSE)
        return httpx.Response(404)

    transport = httpx.MockTransport(counting_handler)

    with _patch_client(transport):
        first = await v.verify_token("cached-tok")
        second = await v.verify_token("cached-tok")

    assert first is not None
    assert second is not None
    assert call_count == 1


# ---------------------------------------------------------------------------
# Scope extraction
# ---------------------------------------------------------------------------


def test_extract_scopes_space_separated():
    assert DiscoveryTokenVerifier._extract_scopes({"scope": "read write delete"}) == [
        "read",
        "write",
        "delete",
    ]


def test_extract_scopes_list():
    assert DiscoveryTokenVerifier._extract_scopes({"scope": ["read", "write"]}) == ["read", "write"]


def test_extract_scopes_missing():
    assert DiscoveryTokenVerifier._extract_scopes({}) == []


# ---------------------------------------------------------------------------
# resolve_token — fallback to LENSES_API_KEY
# ---------------------------------------------------------------------------


def test_resolve_token_falls_back_to_api_key():
    """When no OAuth context exists, resolve_token returns the static API key."""
    api_key = "static-key-123"
    with patch("auth.LENSES_API_KEY", api_key):
        assert resolve_token() == api_key


@patch("auth.LENSES_API_KEY", "")
def test_resolve_token_raises_without_any_credential():
    """ToolError is raised when neither OAuth context nor API key are available."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="Authentication required"):
        resolve_token()
