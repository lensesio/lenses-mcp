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
# resolve_token — API-key mode (OAUTH_ENABLED=False)
# ---------------------------------------------------------------------------


@patch("auth.OAUTH_ENABLED", False)
def test_resolve_token_returns_api_key_when_oauth_off():
    """With OAUTH_ENABLED=False, resolve_token returns the static API key."""
    api_key = "static-key-123"
    with patch("auth.LENSES_API_KEY", api_key):
        assert resolve_token() == api_key


@patch("auth.OAUTH_ENABLED", False)
@patch("auth.LENSES_API_KEY", "")
def test_resolve_token_raises_without_api_key():
    """ToolError when OAUTH_ENABLED=False and LENSES_API_KEY is empty."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="LENSES_API_KEY"):
        resolve_token()


# ---------------------------------------------------------------------------
# resolve_token — OAuth mode (OAUTH_ENABLED=True)
# ---------------------------------------------------------------------------


@patch("auth.OAUTH_ENABLED", True)
def test_resolve_token_raises_when_oauth_on_and_no_context():
    """ToolError when OAUTH_ENABLED=True but no OAuth context is present."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="no OAuth token"):
        resolve_token()


# ---------------------------------------------------------------------------
# Cache invalidation — DiscoveryTokenVerifier.invalidate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_removes_cached_entry():
    """invalidate() evicts a previously-cached introspection result."""
    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect", cache_ttl=300)
    transport = _mock_transport()

    with _patch_client(transport):
        assert await v.verify_token("tok") is not None
    assert v._get_cached("tok") is not None

    v.invalidate("tok")
    assert v._get_cached("tok") is None


def test_invalidate_noop_when_caching_disabled():
    """With cache_ttl=0 (default), invalidate() is a safe no-op."""
    v = _build_verifier()  # cache_ttl defaults to None → 0
    v.invalidate("never-cached-token")  # must not raise


def test_invalidate_unknown_token_noop():
    """Invalidating a token that was never cached is a no-op."""
    v = _build_verifier(cache_ttl=300)
    v.invalidate("never-inserted")  # must not raise


@pytest.mark.asyncio
async def test_invalidate_forces_fresh_introspection_on_next_call():
    """After invalidation, the next verify_token() call re-introspects."""
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
        await v.verify_token("tok")  # call 1
        assert call_count == 1
        await v.verify_token("tok")  # cached
        assert call_count == 1

        v.invalidate("tok")
        await v.verify_token("tok")  # refetch
        assert call_count == 2


# ---------------------------------------------------------------------------
# invalidate_cached_token — server-lookup bridge
# ---------------------------------------------------------------------------


def _mock_server_with_verifier(verifier):
    """Build a mock FastMCP server whose `.auth.token_verifier` is ``verifier``."""
    from unittest.mock import MagicMock

    server = MagicMock()
    server.auth.token_verifier = verifier
    return server


def test_invalidate_cached_token_noop_outside_request_context():
    """Outside a request context, invalidate_cached_token is a safe no-op.

    Covers the stdio / startup / unauthenticated-deployment cases where
    ``get_server()`` raises ``RuntimeError``.
    """
    from auth import invalidate_cached_token

    with patch("fastmcp.server.dependencies.get_server", side_effect=RuntimeError):
        invalidate_cached_token("any-token")  # must not raise


def test_invalidate_cached_token_noop_without_auth_provider():
    """No-op when the active server has no auth provider."""
    from unittest.mock import MagicMock

    from auth import invalidate_cached_token

    server = MagicMock()
    server.auth = None  # unauthenticated deployment
    with patch("fastmcp.server.dependencies.get_server", return_value=server):
        invalidate_cached_token("any-token")  # must not raise


@pytest.mark.asyncio
async def test_invalidate_cached_token_delegates_to_verifier():
    """invalidate_cached_token evicts the cache entry on the active server's verifier."""
    from auth import invalidate_cached_token

    v = _build_verifier(introspection_url=f"{AUTH_SERVER}/oauth2/introspect", cache_ttl=300)
    transport = _mock_transport()
    with _patch_client(transport):
        await v.verify_token("bridge-tok")
    assert v._get_cached("bridge-tok") is not None

    with patch("fastmcp.server.dependencies.get_server", return_value=_mock_server_with_verifier(v)):
        invalidate_cached_token("bridge-tok")
    assert v._get_cached("bridge-tok") is None


def test_invalidate_cached_token_ignores_foreign_verifier():
    """If the active server's verifier isn't a DiscoveryTokenVerifier, silently no-op.

    Future-proofs against deployments that swap in a different TokenVerifier
    implementation — we don't want to blow up, we just can't evict its cache.
    """
    from unittest.mock import MagicMock

    from auth import invalidate_cached_token

    foreign = MagicMock(spec=[])  # not a DiscoveryTokenVerifier
    with patch("fastmcp.server.dependencies.get_server", return_value=_mock_server_with_verifier(foreign)):
        invalidate_cached_token("any-token")  # must not raise


# ---------------------------------------------------------------------------
# AuthenticationRequiredError
# ---------------------------------------------------------------------------


def test_authentication_required_error_is_tool_error():
    """AuthenticationRequiredError is a ToolError subclass so FastMCP surfaces it."""
    from auth import AuthenticationRequiredError
    from fastmcp.exceptions import ToolError

    assert issubclass(AuthenticationRequiredError, ToolError)


def test_authentication_required_error_preserves_message():
    """The message passed at construction is recoverable via str()."""
    from auth import AuthenticationRequiredError

    err = AuthenticationRequiredError("please re-authenticate")
    assert "please re-authenticate" in str(err)


# ---------------------------------------------------------------------------
# handle_downstream_401 — shared 401-to-re-auth-signal helper
# ---------------------------------------------------------------------------


def test_handle_downstream_401_returns_authentication_required_error():
    """The helper returns (not raises) an AuthenticationRequiredError."""
    from unittest.mock import MagicMock

    from auth import AuthenticationRequiredError, handle_downstream_401

    with patch("auth.invalidate_cached_token"):
        err = handle_downstream_401("tok", detail="token revoked", context="with 401", client_logger=MagicMock())
    assert isinstance(err, AuthenticationRequiredError)
    assert "token revoked" in str(err)
    assert "re-authenticate" in str(err)


def test_handle_downstream_401_invalidates_token():
    """The helper calls invalidate_cached_token with the raw token."""
    from unittest.mock import MagicMock

    from auth import handle_downstream_401

    with patch("auth.invalidate_cached_token") as mock_invalidate:
        handle_downstream_401("tok", detail="d", context="c", client_logger=MagicMock())
    mock_invalidate.assert_called_once_with("tok")


def test_handle_downstream_401_still_returns_error_when_invalidator_fails():
    """A failing invalidator must NOT shadow the re-auth signal."""
    from unittest.mock import MagicMock

    from auth import AuthenticationRequiredError, handle_downstream_401

    with patch("auth.invalidate_cached_token", side_effect=RuntimeError("cache down")):
        err = handle_downstream_401("tok", detail="d", context="c", client_logger=MagicMock())
    assert isinstance(err, AuthenticationRequiredError)


def test_handle_downstream_401_logs_warning_with_fingerprint():
    """The warning log must include the token fingerprint for multi-user correlation."""
    from unittest.mock import MagicMock

    from auth import handle_downstream_401, token_fingerprint

    mock_logger = MagicMock()
    with patch("auth.invalidate_cached_token"):
        handle_downstream_401("tok", detail="d", context="with 401", client_logger=mock_logger)

    expected_fp = token_fingerprint("tok")
    all_args = [arg for call in mock_logger.warning.call_args_list for arg in call.args]
    assert any(expected_fp in str(arg) for arg in all_args), (
        f"Expected fingerprint {expected_fp!r} in log args, got {mock_logger.warning.call_args_list!r}"
    )


def test_handle_downstream_401_uses_provided_client_logger():
    """The helper logs via the passed-in logger, not a module-level one.

    This is what lets each caller (HTTPClient, WebSocketClient) keep its own
    logger name in the output — important for operators with log routing.
    """
    from unittest.mock import MagicMock

    from auth import handle_downstream_401

    mock_logger = MagicMock()
    with patch("auth.invalidate_cached_token"):
        handle_downstream_401("tok", detail="d", context="with 401", client_logger=mock_logger)
    assert mock_logger.warning.called


# ---------------------------------------------------------------------------
# token_fingerprint — log correlation for multi-user OAuth deployments
# ---------------------------------------------------------------------------


def test_token_fingerprint_is_deterministic():
    """Same token → same fingerprint, always."""
    from auth import token_fingerprint

    assert token_fingerprint("abc") == token_fingerprint("abc")


def test_token_fingerprint_differs_across_tokens():
    """Different tokens produce different fingerprints."""
    from auth import token_fingerprint

    assert token_fingerprint("abc") != token_fingerprint("def")


def test_token_fingerprint_is_eight_hex_chars():
    """Fingerprints are exactly eight hex characters — short enough to skim in logs."""
    import string

    from auth import token_fingerprint

    fp = token_fingerprint("some-token")
    assert len(fp) == 8
    assert all(c in string.hexdigits for c in fp)


def test_token_fingerprint_is_prefix_of_cache_key():
    """The log fingerprint is a string prefix of DiscoveryTokenVerifier's cache key.

    This lets an operator with access to both logs and a cache dump match
    entries by string prefix — a deliberate design property we lock in here.
    """
    from auth import DiscoveryTokenVerifier, token_fingerprint

    assert DiscoveryTokenVerifier._hash_token("some-token").startswith(token_fingerprint("some-token"))


def test_token_fingerprint_does_not_contain_raw_token():
    """Sanity: the raw token must not leak into the fingerprint."""
    from auth import token_fingerprint

    raw = "SuperSecretOpaqueToken-xyz123"
    fp = token_fingerprint(raw)
    assert raw not in fp
    assert "Secret" not in fp
