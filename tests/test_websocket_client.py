"""Tests for the Lenses WebSocket client — 401 handshake handling and cache invalidation."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from websockets.exceptions import InvalidStatus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

from auth import AuthenticationRequiredError
from clients.websocket_client import LensesWebSocketClient


def _fake_response(status_code: int) -> MagicMock:
    """Build a minimal response object matching what InvalidStatus expects."""
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _raising_connect(status_code: int):
    """Return a stand-in for websockets.connect that raises InvalidStatus on call.

    Unlike the real connect (which returns an awaitable context manager), this
    raises synchronously — enough to exercise the handshake-rejection path.
    """

    def _connect(*args, **kwargs):
        raise InvalidStatus(_fake_response(status_code))

    return _connect


@pytest.fixture(autouse=True)
def _stub_resolve_token():
    """Provide a deterministic token without depending on OAuth context or env vars."""
    with patch("clients.websocket_client.resolve_token", return_value="test-token"):
        yield


@pytest.fixture(autouse=True)
def _stub_invalidate_cached_token():
    """Stop `handle_downstream_401` from touching the real FastMCP server lookup."""
    with patch("auth.invalidate_cached_token") as mock:
        yield mock


# ---------------------------------------------------------------------------
# 401 handshake rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_401_raises_authentication_required_error():
    """A 401 during WebSocket handshake surfaces as AuthenticationRequiredError."""
    client = LensesWebSocketClient()
    with (
        patch("clients.websocket_client.websockets.connect", _raising_connect(401)),
        pytest.raises(AuthenticationRequiredError) as exc_info,
    ):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")

    msg = str(exc_info.value)
    assert "Authentication error" in msg
    assert "re-authenticate" in msg


@pytest.mark.asyncio
async def test_websocket_401_invalidates_cached_token(_stub_invalidate_cached_token):
    """A 401 handshake triggers cache eviction for the forwarded token."""
    client = LensesWebSocketClient()
    with (
        patch("clients.websocket_client.websockets.connect", _raising_connect(401)),
        pytest.raises(AuthenticationRequiredError),
    ):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")
    _stub_invalidate_cached_token.assert_called_once_with("test-token")


@pytest.mark.asyncio
async def test_websocket_401_still_raises_when_invalidator_fails():
    """Defensive: a broken cache layer must not shadow the re-auth signal."""
    client = LensesWebSocketClient()
    with (
        patch("auth.invalidate_cached_token", side_effect=RuntimeError("cache down")),
        patch("clients.websocket_client.websockets.connect", _raising_connect(401)),
        pytest.raises(AuthenticationRequiredError),
    ):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")


@pytest.mark.asyncio
async def test_websocket_401_log_includes_token_fingerprint():
    """Multi-user correlation: the WebSocket 401 warning log must include the fingerprint."""
    import clients.websocket_client as ws_module
    from auth import token_fingerprint

    expected_fp = token_fingerprint("test-token")
    client = LensesWebSocketClient()
    with (
        patch("clients.websocket_client.websockets.connect", _raising_connect(401)),
        patch.object(ws_module.logger, "warning") as mock_warning,
        pytest.raises(AuthenticationRequiredError),
    ):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")

    all_args = [arg for call in mock_warning.call_args_list for arg in call.args]
    assert any(expected_fp in str(arg) for arg in all_args), (
        f"Expected fingerprint {expected_fp!r} in warning log args, got {mock_warning.call_args_list!r}"
    )


# ---------------------------------------------------------------------------
# Non-401 rejection — existing behavior preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_non_401_does_not_raise_authentication_required():
    """A 500 during WebSocket handshake is NOT mapped to AuthenticationRequiredError."""
    client = LensesWebSocketClient()
    with patch("clients.websocket_client.websockets.connect", _raising_connect(500)), pytest.raises(InvalidStatus):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")


@pytest.mark.asyncio
async def test_websocket_non_401_does_not_invalidate_cache(_stub_invalidate_cached_token):
    """A 500 must not touch the introspection cache — it's not an auth failure."""
    client = LensesWebSocketClient()
    with patch("clients.websocket_client.websockets.connect", _raising_connect(500)), pytest.raises(InvalidStatus):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")
    _stub_invalidate_cached_token.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_403_treated_as_generic_error(_stub_invalidate_cached_token):
    """403 is a permission problem, not an auth problem — no re-auth, no cache eviction."""
    client = LensesWebSocketClient()
    with (
        patch("clients.websocket_client.websockets.connect", _raising_connect(403)),
        pytest.raises(InvalidStatus) as exc_info,
    ):
        await client._make_request("/api/v1/sql/execute", "SELECT 1")

    assert not isinstance(exc_info.value, AuthenticationRequiredError)
    _stub_invalidate_cached_token.assert_not_called()
