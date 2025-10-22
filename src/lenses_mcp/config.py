import os

from dotenv import load_dotenv

load_dotenv()


LENSES_API_HTTP_URL = os.getenv("LENSES_API_HTTP_URL", "http://localhost")
LENSES_API_HTTP_PORT = os.getenv("LENSES_API_HTTP_PORT", "9991")

LENSES_API_WEBSOCKET_URL = os.getenv("LENSES_API_WEBSOCKET_URL", "ws://localhost")
LENSES_API_WEBSOCKET_PORT = os.getenv("LENSES_API_WEBSOCKET_PORT", "9991")

LENSES_API_KEY= os.getenv("LENSES_API_KEY", "")
