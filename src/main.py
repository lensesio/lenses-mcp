"""
Lenses MCP Server for interacting with Lenses HQ.
"""
from mcp.server.fastmcp import FastMCP

from common.config import LENSES_HOST_URL, LENSES_PORT, MCP_TRANSPORT
from tools.environments import register_environments
from tools.topics import register_topics


mcp = FastMCP(
    name="Lenses MCP Server",
    instructions="This server provides access to Lenses HQ.",
    stateless_http=True
)

# Register all tools in Lenses modules
register_environments(mcp)
register_topics(mcp)


if __name__ == "__main__":
    print("Starting Lenses MCP Server")
    print(f"API base URL: {LENSES_HOST_URL}:{LENSES_PORT}")
    print(f"Tools count: {len(mcp.list_tools())}")
    
    mcp.run(transport=MCP_TRANSPORT)
