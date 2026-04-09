"""WebSocket client for Lenses API operations.

Each call opens a fresh websocket connection — client-side websockets in the
stdlib have no pooling concept, so connection-per-call is inherent rather
than a workaround. The `Authorization` header is rebuilt per call via
`auth.resolve_token()`, so each caller's bearer token is forwarded to Lenses
without leaking across concurrent requests.
"""

import json
from typing import Any

import websockets
from auth import resolve_token
from config import LENSES_API_WEBSOCKET_PORT, LENSES_API_WEBSOCKET_URL
from loguru import logger

logger = logger.bind(name="WebSocketClient")

LENSES_API_WEBSOCKET_BASE_URL = f"{LENSES_API_WEBSOCKET_URL}:{LENSES_API_WEBSOCKET_PORT}"


class LensesWebSocketClient:
    def __init__(self, base_url: str = LENSES_API_WEBSOCKET_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _make_request(self, endpoint: str, sql: str) -> list[dict[str, Any]]:
        uri = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {resolve_token()}"}

        try:
            async with websockets.connect(uri=uri, additional_headers=headers) as ws:
                records: list[dict[str, Any]] = []
                await ws.send(json.dumps({"sql": sql}))

                while True:
                    response = await ws.recv()
                    if isinstance(response, bytes):
                        response = response.decode()
                    logger.info(f"Message received: {response}")

                    data = json.loads(response)
                    message_type = data["type"].upper()

                    match message_type:
                        case "RECORD":
                            data_ = data.get("data")

                            if not data_:
                                return records

                            records.append(data_)
                            logger.info(f"Record appended: {data_}")
                        case "END":
                            logger.info(f"Stream ended. Received records count: {len(records)}")
                            return records
                        case "ERROR":
                            logger.info(f"Error encountered: {data}")
                            return records
                        case _:
                            logger.info(f"Discarding unsupported message type: {message_type}")
        except Exception as e:
            logger.error(f"Unhandled error while fetching messages: {e}")
            raise e


websocket_client = LensesWebSocketClient()
