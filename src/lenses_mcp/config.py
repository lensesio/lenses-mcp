from __future__ import annotations

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastmcp.server.auth import require_scopes
from loguru import logger

load_dotenv()


# New simplified config: single LENSES_URL
LENSES_URL = os.getenv("LENSES_URL", "http://localhost:9991")

# Parse the URL to extract components
parsed_url = urlparse(LENSES_URL)
scheme = parsed_url.scheme or "http"
hostname = parsed_url.hostname or "localhost"

# Determine port: use explicit port, or default based on scheme
port = str(parsed_url.port) if parsed_url.port else "443" if scheme == "https" else "80" if scheme == "http" else "9991"

# Derive HTTP and WebSocket URLs from LENSES_URL
# If scheme is https, use wss for websockets; otherwise use ws
websocket_scheme = "wss" if scheme == "https" else "ws"

LENSES_API_HTTP_URL = f"{scheme}://{hostname}"
LENSES_API_HTTP_PORT = port
LENSES_API_WEBSOCKET_URL = f"{websocket_scheme}://{hostname}"
LENSES_API_WEBSOCKET_PORT = port

# Backward compatibility: allow override with legacy env vars
LENSES_API_HTTP_URL = os.getenv("LENSES_API_HTTP_URL", LENSES_API_HTTP_URL)
LENSES_API_HTTP_PORT = os.getenv("LENSES_API_HTTP_PORT", LENSES_API_HTTP_PORT)
LENSES_API_WEBSOCKET_URL = os.getenv("LENSES_API_WEBSOCKET_URL", LENSES_API_WEBSOCKET_URL)
LENSES_API_WEBSOCKET_PORT = os.getenv("LENSES_API_WEBSOCKET_PORT", LENSES_API_WEBSOCKET_PORT)

LENSES_API_KEY = os.getenv("LENSES_API_KEY", "")

# ── Authentication mode toggle ────────────────────────────────────────
# OAUTH_ENABLED switches between two mutually-exclusive auth modes:
#   True  → OAuth 2.1 (requires MCP_ADVERTISED_URL and LENSES_ADVERTISED_URL)
#   False → Static API key (requires LENSES_API_KEY)
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "false").lower() in ("true", "1", "yes")

# OAuth 2.1 gateway config.
#
# MCP_ADVERTISED_URL is the public URL at which this MCP server is reachable by
# clients. It is published as the "resource" field in the protected-resource
# metadata and must exactly match the URL clients use to connect (scheme, host,
# path prefix) — otherwise strict MCP clients will reject the metadata as
# mismatched.
#
# LENSES_ADVERTISED_URL is the public URL of Lenses HQ that MCP clients are
# directed to for OAuth login. It is *advertised* in the protected-resource
# metadata, never contacted by the MCP server itself. In simple deployments
# where the MCP server and the MCP client both reach Lenses on the same URL,
# leave it unset: it defaults to LENSES_URL. Override only in split-plane
# deployments where the MCP server reaches Lenses over an internal address
# (e.g. cluster DNS) while clients reach it over a public one.
MCP_ADVERTISED_URL = os.getenv("MCP_ADVERTISED_URL")
LENSES_ADVERTISED_URL = os.getenv("LENSES_ADVERTISED_URL") or LENSES_URL
if LENSES_ADVERTISED_URL == LENSES_URL and not os.getenv("LENSES_ADVERTISED_URL"):
    logger.info("LENSES_ADVERTISED_URL not set, defaulting to LENSES_URL ({})", LENSES_URL)
# Scopes the resource requires. Published in protected-resource metadata so
# compliant clients include them in their /authorize request.
MCP_SCOPES = [s.strip() for s in os.getenv("MCP_SCOPES", "read,write,delete").split(",") if s.strip()]

# MCP server transport configuration.
# Defaults to "http" whenever OAuth is enabled, otherwise "stdio" for local
# development with LENSES_API_KEY. Set TRANSPORT explicitly to opt into
# "streamable-http", "sse", or to force a specific mode.
TRANSPORT = os.getenv("TRANSPORT") or ("http" if OAUTH_ENABLED else "stdio")
HOST = os.getenv("HOST", "0.0.0.0")  # noqa: S104
PORT = int(os.getenv("PORT", "8000"))
# Consumed directly by FastMCP internals; surfaced here for visibility/logging.
FASTMCP_STATELESS_HTTP = os.getenv("FASTMCP_STATELESS_HTTP", "false")

# RFC 7662 Token Introspection config.
# The introspection URL is discovered from .well-known/oauth-authorization-server
# metadata unless explicitly overridden here. The introspection endpoint is
# called without client authentication.
INTROSPECTION_URL = os.getenv("INTROSPECTION_URL")
INTROSPECTION_CACHE_TTL = int(os.getenv("INTROSPECTION_CACHE_TTL", "0"))


# ── Startup validation ────────────────────────────────────────────────


def _validate_auth_config() -> None:
    """Fail fast if the required env vars for the chosen auth mode are missing."""
    if OAUTH_ENABLED:
        missing: list[str] = []
        if not MCP_ADVERTISED_URL:
            missing.append("MCP_ADVERTISED_URL")
        if not os.getenv("LENSES_ADVERTISED_URL") and not LENSES_URL:
            missing.append("LENSES_ADVERTISED_URL")
        if missing:
            raise OSError(
                f"OAUTH_ENABLED=true but the following required variable(s) are not set: {', '.join(missing)}"
            )
    else:
        if not LENSES_API_KEY:
            raise OSError("OAUTH_ENABLED=false (API-key mode) but LENSES_API_KEY is not set")


_validate_auth_config()


# ── Conditional scope enforcement ─────────────────────────────────────


def oauth_required_scopes(*scopes: str):
    """Return a ``require_scopes`` dependency when OAuth is on, else ``None``.

    Used as the ``auth`` argument on every ``@mcp.tool()`` decorator so that
    scope checks are only enforced in OAuth deployments.
    """
    if OAUTH_ENABLED:
        return require_scopes(*scopes)
    return None
