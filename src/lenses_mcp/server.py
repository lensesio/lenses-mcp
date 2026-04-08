"""
Lenses MCP Server for interacting with Lenses HQ.
"""

from auth import PassthroughTokenVerifier
from config import (
    AUTH_SERVER_URL,
    FASTMCP_STATELESS_HTTP,
    HOST,
    LENSES_API_HTTP_PORT,
    LENSES_API_HTTP_URL,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL,
    MCP_SCOPES,
    MCP_SERVER_BASE_URL,
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

# Wire RemoteAuthProvider only when AUTH_SERVER_URL is set. Without it, the
# server runs unauthenticated and tools fall back to the static LENSES_API_KEY
# (legacy / stdio behavior — see auth.resolve_token).
auth = None
if AUTH_SERVER_URL:
    if not MCP_SERVER_BASE_URL:
        raise RuntimeError("MCP_SERVER_BASE_URL must be set when AUTH_SERVER_URL is set")
    auth = RemoteAuthProvider(
        token_verifier=PassthroughTokenVerifier(),
        authorization_servers=[AnyHttpUrl(AUTH_SERVER_URL)],
        base_url=MCP_SERVER_BASE_URL,
        scopes_supported=MCP_SCOPES,
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
