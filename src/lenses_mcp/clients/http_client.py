from typing import Any, Dict, Optional

import httpx
from config import LENSES_API_HTTP_PORT, LENSES_API_HTTP_URL, LENSES_API_KEY
from loguru import logger

logger = logger.bind(name="HTTPClient")

LENSES_API_HTTP_BASE_URL = f"{LENSES_API_HTTP_URL}:{LENSES_API_HTTP_PORT}"

"""HTTP client for Lenses API operations."""
class LensesAPIClient:
    
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data if data else None,
                    timeout=30.0
                )
                
                if response.status_code == 204:  # No content (delete operation)
                    return {"success": True, "message": "Operation completed successfully"}
                
                response.raise_for_status()
                
                # Handle empty responses
                if not response.content:
                    return {"success": True}
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_detail = "Unknown error"
                try:
                    error_response = e.response.json()
                    error_detail = error_response.get("title", f"HTTP {e.response.status_code}: {e.response.text}")
                except Exception:
                    error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                
                error_message = f"API request failed: {error_detail}"
                logger.error(error_message)
                raise Exception(error_message)
            except httpx.RequestError as e:
                error_message = f"Network error: {str(e)}"
                logger.error(error_message)
                raise Exception(error_message)


api_client = LensesAPIClient(LENSES_API_HTTP_BASE_URL, LENSES_API_KEY)
