import json
from typing import Any, Dict, List

import websockets
from config import (
    LENSES_API_KEY,
    LENSES_API_WEBSOCKET_PORT,
    LENSES_API_WEBSOCKET_URL,
)
from loguru import logger

logger = logger.bind(name="LensesMCPTools")

LENSES_API_WEBSOCKET_BASE_URL = f"{LENSES_API_WEBSOCKET_URL}:{LENSES_API_WEBSOCKET_PORT}"


"""WebSocket client for Lenses API operations."""
class LensesWebSocketClient:

    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {bearer_token}"
        }
    
    async def _make_request(
        self,
        endpoint: str,
        sql: str
    ) -> List[Dict[str, Any]]:
        uri = f"{self.base_url}{endpoint}"

        try:
            async with websockets.connect(
                uri=uri,
                additional_headers=self.headers
            ) as ws:
                records = []
                await ws.send(json.dumps({"sql": sql}))
                
                while True:
                    response = await ws.recv()
                    logger.info(f"Message received: {response}")

                    data = json.loads(response)
                    message_type = data["type"].upper()

                    match message_type:
                        case "RECORD":
                            # record = MessageRecord()
                            # data_ = data.get("data")

                            # if not data_:
                            #     return

                            # for key, value in data_.items():
                            #     record.set_key(key, value)

                            # records.append(record)
                            # logger.info(f"Record appended: {record}")

                            data_ = data.get("data")

                            if not data_:
                                return
                            
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
            logger.info(f"Unhandled error while fetching messages: {e}")
            raise e


websocket_client = LensesWebSocketClient(LENSES_API_WEBSOCKET_BASE_URL, LENSES_API_KEY)
