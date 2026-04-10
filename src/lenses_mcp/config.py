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

# OAuth 2.1 gateway config. OAuth is enabled when MCP_ADVERTISED_URL is set —
# this is the signal that the MCP server is being deployed somewhere clients
# need to reach over the network. When unset, the server runs without
# RemoteAuthProvider and tools fall back to the static LENSES_API_KEY
# (legacy / stdio behavior — see auth.resolve_token).
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
LENSES_ADVERTISED_URL = os.getenv("LENSES_ADVERTISED_URL", LENSES_URL)
# Scopes the resource requires. Published in protected-resource metadata so
# compliant clients include them in their /authorize request.
MCP_SCOPES = [s.strip() for s in os.getenv("MCP_SCOPES", "read,write,delete").split(",") if s.strip()]

# MCP server transport configuration.
# Defaults to "http" whenever OAuth is enabled (MCP_ADVERTISED_URL is set),
# otherwise "stdio" for local development with LENSES_API_KEY. Set TRANSPORT
# explicitly to opt into "streamable-http", "sse", or to force a specific mode.
TRANSPORT = os.getenv("TRANSPORT") or ("http" if MCP_ADVERTISED_URL else "stdio")
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
