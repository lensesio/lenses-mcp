"""
Lenses MCP Server for interacting with Lenses HQ.
"""

from auth import DiscoveryTokenVerifier
from config import (
    FASTMCP_STATELESS_HTTP,
    HOST,
    INTROSPECTION_CACHE_TTL,
    INTROSPECTION_URL,
    LENSES_ADVERTISED_URL,
    LENSES_API_HTTP_PORT,
    LENSES_API_HTTP_URL,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL,
    MCP_ADVERTISED_URL,
    MCP_SCOPES,
    PORT,
    TRANSPORT,
)
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from loguru import logger
from pydantic import AnyHttpUrl
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from tools.environments import register_environments
from tools.kafka_connectors import register_kafka_connectors
from tools.kafka_consumer_groups import register_kafka_consumer_groups
from tools.sql import register_sql
from tools.sql_processors import register_sql_processors
from tools.topics import register_topics

logger = logger.bind(name="MCPServer")

logger.info("Starting Lenses MCP Server")
logger.info(f"Transport: {TRANSPORT}")
if TRANSPORT != "stdio":
    logger.info(f"Listening on: {HOST}:{PORT}")
    logger.info(f"Stateless HTTP: {FASTMCP_STATELESS_HTTP}")
logger.info(f"Lenses API HTTP URL: {LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}")
logger.info(f"Lenses API WebSocket URL: {LENSES_API_WEBSOCKET_URL}:{LENSES_API_WEBSOCKET_PORT}")


def build_auth_provider(
    *,
    mcp_advertised_url: str | None,
    lenses_advertised_url: str,
    internal_lenses_base: str,
    introspection_url: str | None,
    introspection_cache_ttl: int,
    mcp_scopes: list[str],
) -> RemoteAuthProvider | None:
    """Construct the OAuth resource-server provider, or return None when OAuth is off.

    Wires RemoteAuthProvider only when ``mcp_advertised_url`` is set — that's
    the signal the operator is deploying publicly. Without it, the server runs
    unauthenticated and tools fall back to the static LENSES_API_KEY (legacy /
    stdio behavior — see ``auth.resolve_token``).

    Split-plane invariant: introspection MUST use ``internal_lenses_base`` (the
    same composition the data-plane HTTP client uses), NOT
    ``lenses_advertised_url``. The advertised URL is for clients only and may
    not be reachable from inside the MCP server's network. We also bypass
    metadata discovery entirely by passing ``introspection_url`` explicitly:
    Lenses HQ would advertise its public URL in the .well-known response,
    which we cannot reach from inside the cluster.

    Extracted as a pure function so tests can exercise every config combination
    without monkey-patching ``sys.modules``.
    """
    if not mcp_advertised_url:
        return None
    return RemoteAuthProvider(
        token_verifier=DiscoveryTokenVerifier(
            auth_server_url=internal_lenses_base,
            introspection_url=introspection_url or f"{internal_lenses_base}/oauth2/introspect",
            cache_ttl_seconds=introspection_cache_ttl if introspection_cache_ttl > 0 else None,
        ),
        authorization_servers=[AnyHttpUrl(lenses_advertised_url)],
        base_url=mcp_advertised_url,
        scopes_supported=mcp_scopes,
    )


auth = build_auth_provider(
    mcp_advertised_url=MCP_ADVERTISED_URL,
    lenses_advertised_url=LENSES_ADVERTISED_URL,
    internal_lenses_base=f"{LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}",
    introspection_url=INTROSPECTION_URL,
    introspection_cache_ttl=INTROSPECTION_CACHE_TTL,
    mcp_scopes=MCP_SCOPES,
)

mcp = FastMCP("Lenses.io", auth=auth, mask_error_details=True)

# Register all Lenses tools modules
register_environments(mcp)
register_kafka_connectors(mcp)
register_kafka_consumer_groups(mcp)
register_sql(mcp)
register_sql_processors(mcp)
register_topics(mcp)


if __name__ == "__main__":
    run_kwargs: dict = {"transport": TRANSPORT}
    if TRANSPORT != "stdio":
        run_kwargs["host"] = HOST
        run_kwargs["port"] = PORT
        # CORS: allow all origins so browser-based MCP clients (e.g. mcp-inspector
        # web UI) can complete their preflight + OAuth discovery flow. Bearer-token
        # auth means we don't need allow_credentials, so wildcard origin is safe.
        # `WWW-Authenticate` must be exposed for the OAuth challenge to reach JS.
        run_kwargs["middleware"] = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["mcp-session-id", "WWW-Authenticate"],
            )
        ]
    mcp.run(**run_kwargs)
