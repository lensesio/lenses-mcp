"""
Lenses MCP Server for interacting with Lenses HQ.
"""
from fastmcp import settings, FastMCP

from config import LENSES_HOST_URL, LENSES_PORT, MCP_TRANSPORT
from tools.environments import register_environments
from tools.topics import register_topics

settings.log_level = "DEBUG"
settings.stateless_http = True

mcp = FastMCP(
    name="Lenses MCP Server",
    instructions="This server provides access to Lenses HQ."
)

# Register all tools in Lenses modules
register_environments(mcp)
register_topics(mcp)


if __name__ == "__main__":
    print("Starting Lenses MCP Server")
    print(f"API base URL: {LENSES_HOST_URL}:{LENSES_PORT}")
    print(f"Tools count: {len(mcp.list_tools())}")
    
    mcp.run(transport=MCP_TRANSPORT)
