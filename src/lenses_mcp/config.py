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
