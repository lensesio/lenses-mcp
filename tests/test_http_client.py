"""Tests for the Lenses HTTP client — 401 handling, cache invalidation, and error detail extraction."""

import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

import clients.http_client as http_client_module
from auth import AuthenticationRequiredError
from clients.http_client import LensesAPIClient, _extract_error_detail


@contextmanager
def _mock_lenses_response(status_code: int, body):
    """Replace the shared async client with one that returns a fixed response.

    Restores the original client on exit so tests don't leak state.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(body, dict):
            return httpx.Response(status_code, json=body)
        return httpx.Response(status_code, text=body)

    transport = httpx.MockTransport(handler)
    original = http_client_module._async_client
    http_client_module._async_client = httpx.AsyncClient(transport=transport)
    try:
        yield
    finally:
        http_client_module._async_client = original


@pytest.fixture(autouse=True)
def _stub_resolve_token():
    """Provide a deterministic token without depending on OAuth context or env vars."""
    with patch("clients.http_client.resolve_token", return_value="test-token"):
        yield


@pytest.fixture(autouse=True)
def _stub_invalidate_cached_token():
    """Stop `handle_downstream_401` from touching the real FastMCP server lookup.

    Tests that want to assert on invalidation can re-patch at a narrower scope.
    """
    with patch("auth.invalidate_cached_token") as mock:
        yield mock


# ---------------------------------------------------------------------------
# 401 handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_raises_authentication_required_error():
    """A 401 from Lenses surfaces as AuthenticationRequiredError, not a generic Exception."""
    body = {"title": "Unauthorized", "error_description": "token revoked"}
    client = LensesAPIClient()
    with _mock_lenses_response(401, body), pytest.raises(AuthenticationRequiredError):
        await client._make_request("GET", "/api/v1/topics")


@pytest.mark.asyncio
async def test_401_error_message_includes_lenses_detail_and_reauth_hint():
    """The error message includes both the Lenses error detail and a re-auth prompt."""
    body = {"title": "Unauthorized", "error_description": "token revoked"}
    client = LensesAPIClient()
    with _mock_lenses_response(401, body), pytest.raises(AuthenticationRequiredError) as exc_info:
        await client._make_request("GET", "/api/v1/topics")

    msg = str(exc_info.value)
    assert "Authentication error" in msg
    assert "Unauthorized" in msg  # from Lenses' title
    assert "re-authenticate" in msg  # our user-facing hint


@pytest.mark.asyncio
async def test_401_invalidates_cached_token(_stub_invalidate_cached_token):
    """A 401 from Lenses calls invalidate_cached_token with the forwarded token."""
    client = LensesAPIClient()
    with _mock_lenses_response(401, {"title": "Unauthorized"}), pytest.raises(AuthenticationRequiredError):
        await client._make_request("GET", "/api/v1/topics")
    _stub_invalidate_cached_token.assert_called_once_with("test-token")


@pytest.mark.asyncio
async def test_401_still_raises_when_invalidator_fails():
    """Defensive: a broken cache layer must not shadow the re-auth signal."""
    client = LensesAPIClient()
    with (
        patch("auth.invalidate_cached_token", side_effect=RuntimeError("cache down")),
        _mock_lenses_response(401, {"title": "Unauthorized"}),
        pytest.raises(AuthenticationRequiredError),
    ):
        await client._make_request("GET", "/api/v1/topics")


@pytest.mark.asyncio
async def test_401_log_includes_token_fingerprint():
    """Multi-user correlation: the 401 warning log must include the token fingerprint.

    Dropping the fingerprint in a refactor would silently regress debuggability,
    so pin it down with a test.
    """
    from auth import token_fingerprint

    expected_fp = token_fingerprint("test-token")
    client = LensesAPIClient()
    with (
        _mock_lenses_response(401, {"title": "Unauthorized"}),
        patch.object(http_client_module.logger, "warning") as mock_warning,
        pytest.raises(AuthenticationRequiredError),
    ):
        await client._make_request("GET", "/api/v1/topics")

    all_args = [arg for call in mock_warning.call_args_list for arg in call.args]
    assert any(expected_fp in str(arg) for arg in all_args), (
        f"Expected fingerprint {expected_fp!r} in warning log args, got {mock_warning.call_args_list!r}"
    )


# ---------------------------------------------------------------------------
# Non-401 errors — unchanged behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_401_raises_generic_exception():
    """A 500 still flows through the generic error path, not the auth-required path."""
    client = LensesAPIClient()
    with (
        _mock_lenses_response(500, {"title": "Internal Server Error"}),
        pytest.raises(Exception, match="Internal Server Error") as exc_info,
    ):
        await client._make_request("GET", "/api/v1/topics")
    assert not isinstance(exc_info.value, AuthenticationRequiredError)


@pytest.mark.asyncio
async def test_non_401_does_not_invalidate_cache(_stub_invalidate_cached_token):
    """A 500 from Lenses must NOT touch the introspection cache."""
    client = LensesAPIClient()
    with (
        _mock_lenses_response(500, {"title": "Kaboom"}),
        pytest.raises(Exception, match="Kaboom"),
    ):
        await client._make_request("GET", "/api/v1/topics")
    _stub_invalidate_cached_token.assert_not_called()


@pytest.mark.asyncio
async def test_403_treated_as_generic_error(_stub_invalidate_cached_token):
    """403 is a permission problem, not an auth problem — no re-auth, no cache eviction."""
    client = LensesAPIClient()
    with (
        _mock_lenses_response(403, {"title": "Forbidden"}),
        pytest.raises(Exception, match="Forbidden") as exc_info,
    ):
        await client._make_request("GET", "/api/v1/topics")
    assert not isinstance(exc_info.value, AuthenticationRequiredError)
    _stub_invalidate_cached_token.assert_not_called()


# ---------------------------------------------------------------------------
# _extract_error_detail helper
# ---------------------------------------------------------------------------


def test_extract_error_detail_uses_title_field():
    """RFC 7807 'title' field is preferred when present."""
    resp = httpx.Response(401, json={"title": "Unauthorized", "error_description": "expired"})
    assert _extract_error_detail(resp) == "Unauthorized"


def test_extract_error_detail_falls_back_to_error_description():
    """When no 'title', fall back to OAuth 'error_description'."""
    resp = httpx.Response(401, json={"error_description": "token expired"})
    assert _extract_error_detail(resp) == "token expired"


def test_extract_error_detail_handles_non_json_body():
    """A non-JSON body is surfaced as 'HTTP <status>: <text>'."""
    resp = httpx.Response(500, text="<html>oops</html>")
    detail = _extract_error_detail(resp)
    assert "HTTP 500" in detail
    assert "oops" in detail


def test_extract_error_detail_handles_empty_body():
    """An empty body doesn't crash — returns a stub with the status code."""
    resp = httpx.Response(401, text="")
    assert "HTTP 401" in _extract_error_detail(resp)


def test_extract_error_detail_handles_json_missing_both_fields():
    """JSON without title or error_description falls back to the raw body."""
    resp = httpx.Response(500, json={"unrelated": "value"})
    assert "HTTP 500" in _extract_error_detail(resp)


# ---------------------------------------------------------------------------
# Success paths — regression guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_returns_parsed_json():
    """A successful 200 response returns the parsed JSON body."""
    client = LensesAPIClient()
    with _mock_lenses_response(200, {"topics": ["a", "b"]}):
        result = await client._make_request("GET", "/api/v1/topics")
    assert result == {"topics": ["a", "b"]}


@pytest.mark.asyncio
async def test_204_returns_success_marker():
    """A 204 No Content response returns the success marker."""
    client = LensesAPIClient()
    with _mock_lenses_response(204, ""):
        result = await client._make_request("DELETE", "/api/v1/topics/foo")
    assert result == {"success": True, "message": "Operation completed successfully"}
