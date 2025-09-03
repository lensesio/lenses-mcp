import os
from dotenv import load_dotenv
load_dotenv()


LENSES_HOST_URL = os.getenv("LENSES_HOST_URL", "https://master.lenses.cloud")
LENSES_PORT = os.getenv("LENSES_PORT", "443")
LENSES_API_KEY= os.getenv("LENSES_API_KEY", "")

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
