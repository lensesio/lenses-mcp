"""
Lenses MCP Server for interacting with Lenses HQ.
"""
from config import (
    LENSES_API_HTTP_PORT,
    LENSES_API_HTTP_URL,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL
)
from fastmcp import FastMCP, settings
from loguru import logger
from tools.environments import register_environments
from tools.kafka_consumer_groups import register_kafka_consumer_groups
from tools.sql import register_sql
from tools.topics import register_topics

logger = logger.bind(name="MCPServer")

settings.log_level = "INFO"
settings.stateless_http = True


mcp = FastMCP("Lenses.io")

# Register all Lenses tools modules
register_environments(mcp)
register_kafka_consumer_groups(mcp)
register_sql(mcp)
register_topics(mcp)


if __name__ == "__main__":
    logger.info(f"Starting Lenses MCP Server")
    logger.info(f"API base HTTP URL: {LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}")
    logger.info(f"API base WebSocket URL: {LENSES_API_WEBSOCKET_URL}:{LENSES_API_WEBSOCKET_PORT}")
    
    mcp.run()
