"""HTTP client for Lenses API operations.

Uses a single long-lived `httpx2.AsyncClient` for connection pooling, TLS
session reuse, and HTTP keep-alive. The `Authorization` header is rebuilt
per call via `auth.resolve_token()`, so each caller's bearer token is
forwarded to Lenses without leaking across concurrent requests.
"""

from typing import Any

import httpx2
from auth import handle_downstream_401, resolve_token
from config import LENSES_API_HTTP_PORT, LENSES_API_HTTP_URL
from loguru import logger

logger = logger.bind(name="HTTPClient")

LENSES_API_HTTP_BASE_URL = f"{LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}"

_async_client: httpx2.AsyncClient | None = None


def _get_async_client() -> httpx2.AsyncClient:
    """Lazily construct and return the shared `httpx2.AsyncClient`."""
    global _async_client
    if _async_client is None:
        _async_client = httpx2.AsyncClient(timeout=30.0)
    return _async_client


class LensesAPIError(httpx2.HTTPStatusError):
    """A Lenses API call that came back with a non-2xx status.

    ``str()`` is exactly the message the previously-raised bare ``Exception``
    carried, so callers that only format the error are unaffected. What is new
    is ``status_code``: tools can branch on the HTTP status instead of matching
    substrings in a message whose wording belongs to Lenses HQ, not to us.

    Subclassing httpx2's own status error is deliberate. FastMCP recognises it
    (``fastmcp.utilities.exceptions.is_http_status_error``) and turns an
    upstream 429 into an actionable "retry later" for the model even when
    ``mask_error_details`` is on; a bare ``Exception`` defeats that check.
    """

    @property
    def status_code(self) -> int:
        return self.response.status_code


class LensesAPIClient:
    def __init__(self, base_url: str = LENSES_API_HTTP_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        token = resolve_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        try:
            response = await _get_async_client().request(
                method=method, url=url, headers=headers, json=data if data else None
            )

            if response.status_code == 204:  # No content (delete operation)
                return {"success": True, "message": "Operation completed successfully"}

            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return {"success": True}

            return response.json()

        except httpx2.HTTPStatusError as e:
            error_detail = _extract_error_detail(e.response)

            if e.response.status_code == 401:
                raise handle_downstream_401(token, detail=error_detail, context="with 401", client_logger=logger) from e

            error_message = f"API request failed: {error_detail}"
            logger.error(error_message)
            raise LensesAPIError(error_message, request=e.request, response=e.response) from e
        except httpx2.RequestError as e:
            error_message = f"Network error: {e!s}"
            logger.error(error_message)
            raise Exception(error_message) from e


def _extract_error_detail(response: httpx2.Response) -> str:
    """Best-effort extraction of a human-readable error detail from a Lenses error response.

    Tries JSON first (``title`` or ``error_description``), falling back to the
    raw body with the status code.
    """
    try:
        body = response.json()
        return body.get("title") or body.get("error_description") or f"HTTP {response.status_code}: {response.text}"
    except Exception:
        return f"HTTP {response.status_code}: {response.text}"


api_client = LensesAPIClient()
