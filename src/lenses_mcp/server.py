"""
Lenses MCP Server for interacting with Lenses HQ.
"""
from fastmcp import FastMCP, settings
from loguru import logger

from config import (
    LENSES_API_HTTP_PORT,
    LENSES_API_HTTP_URL,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL,
    MCP_TRANSPORT,
    MCP_HOST,
    MCP_PORT,
)
from tools.environments import register_environments
from tools.sql import register_sql
from tools.topics import register_topics

settings.log_level = "INFO"
settings.stateless_http = True

logger = logger.bind(name="LensesMCPTools")

mcp = FastMCP(
    name="Lenses MCP Server",
    instructions="This server provides access to Lenses HQ."
)

# Register all Lenses tools modules
register_environments(mcp)
register_topics(mcp)
register_sql(mcp)


if __name__ == "__main__":
    logger.info(f"Starting Lenses MCP Server: {MCP_HOST}:{MCP_PORT} with {MCP_TRANSPORT}")
    logger.info(f"API base HTTP URL: {LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}")
    logger.info(f"API base WebSocket URL: {LENSES_API_WEBSOCKET_URL}:{LENSES_API_WEBSOCKET_PORT}")
    logger.info(f"Tools count: {len(mcp.list_tools())}")
    
    mcp.run(
        transport=MCP_TRANSPORT,
        host=MCP_HOST,
        port=MCP_PORT
    )
