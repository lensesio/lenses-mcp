import os

from dotenv import load_dotenv

load_dotenv()


LENSES_API_HTTP_URL = os.getenv("LENSES_API_HTTP_URL", "https://master.lenses.cloud")
LENSES_API_HTTP_PORT = os.getenv("LENSES_API_HTTP_PORT", "443")

LENSES_API_WEBSOCKET_URL = os.getenv("LENSES_API_WEBSOCKET_URL", "wss://master.lenses.cloud")
LENSES_API_WEBSOCKET_PORT = os.getenv("LENSES_API_WEBSOCKET_PORT", "443")

LENSES_API_KEY= os.getenv("LENSES_API_KEY", "")

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
