"""
Lenses MCP Server for interacting with Lenses HQ.
"""

from config import (
    FASTMCP_STATELESS_HTTP,
    HOST,
    LENSES_API_HTTP_PORT,
    LENSES_API_HTTP_URL,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL,
    PORT,
    TRANSPORT,
)
from fastmcp import FastMCP
from loguru import logger
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

mcp = FastMCP("Lenses.io", mask_error_details=True)

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
    mcp.run(**run_kwargs)
