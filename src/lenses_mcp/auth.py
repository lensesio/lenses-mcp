"""Passthrough token verifier — no validation, opaque token forwarding.

The MCP server has no way to validate opaque tokens issued by the auth server
(no JWT to decode, no introspection endpoint). Validation is delegated to the
Lenses API, which will return 401/403 if the token is bad.

This verifier exists only to satisfy `RemoteAuthProvider`'s contract (it
requires a non-None `TokenVerifier`) and to make the raw token available to
tools via `fastmcp.server.dependencies.get_access_token().token`.
"""

from config import LENSES_API_KEY
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token


class PassthroughTokenVerifier(TokenVerifier):
    """Accepts any non-empty Bearer token without inspection."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        return AccessToken(
            token=token,
            client_id="passthrough",
            scopes=[],
            expires_at=None,
        )


def resolve_token() -> str:
    """Bearer token to forward to Lenses for the current call.

    Resolution order:
    1. Per-request token from FastMCP's auth context (OAuth passthrough).
    2. Static `LENSES_API_KEY` from env (legacy / stdio fallback).
    3. ToolError if neither is available.
    """
    try:
        access_token = get_access_token()
    except (LookupError, RuntimeError):
        access_token = None  # outside a request context (e.g. stdio)

    if access_token is not None:
        return access_token.token

    if LENSES_API_KEY:
        return LENSES_API_KEY

    raise ToolError("Authentication required")
