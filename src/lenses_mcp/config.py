import os
from urllib.parse import urlparse

from dotenv import load_dotenv

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

# MCP server transport configuration
TRANSPORT = os.getenv("TRANSPORT", "stdio")
HOST = os.getenv("HOST", "0.0.0.0")  # noqa: S104
PORT = int(os.getenv("PORT", "8000"))
# Consumed directly by FastMCP internals; surfaced here for visibility/logging.
FASTMCP_STATELESS_HTTP = os.getenv("FASTMCP_STATELESS_HTTP", "false")

# OAuth 2.1 gateway config. When AUTH_SERVER_URL is unset, the MCP server runs
# without RemoteAuthProvider and tools fall back to the static LENSES_API_KEY
# (legacy / stdio behavior — see auth.resolve_token).
AUTH_SERVER_URL = os.getenv("AUTH_SERVER_URL")
MCP_SERVER_BASE_URL = os.getenv("MCP_SERVER_BASE_URL")
# Scopes the resource requires. Published in protected-resource metadata so
# compliant clients include them in their /authorize request.
MCP_SCOPES = [s.strip() for s in os.getenv("MCP_SCOPES", "read,write,delete").split(",") if s.strip()]

# RFC 7662 Token Introspection config.
# The introspection URL is discovered from .well-known/oauth-authorization-server
# metadata unless explicitly overridden here. The introspection endpoint is
# called without client authentication.
INTROSPECTION_URL = os.getenv("INTROSPECTION_URL")
INTROSPECTION_CACHE_TTL = int(os.getenv("INTROSPECTION_CACHE_TTL", "0"))
