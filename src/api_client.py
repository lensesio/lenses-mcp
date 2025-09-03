import httpx
import os
from typing import Any, Dict, Optional
from config import LENSES_HOST_URL, LENSES_PORT

LENSES_API_BASE_URL = f"{LENSES_HOST_URL}:{LENSES_PORT}"
LENSES_API_KEY = os.getenv("LENSES_API_KEY", "")


"""HTTP client for Lenses API operations."""
class LensesAPIClient:
    
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip('/')
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
        """Make HTTP request to Lenses API."""
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
                    error_detail = error_response.get("title", f"HTTP {e.response.status_code}")
                except:
                    error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                
                raise Exception(f"API request failed: {error_detail}")
            except httpx.RequestError as e:
                raise Exception(f"Network error: {str(e)}")

api_client = LensesAPIClient(LENSES_API_BASE_URL, LENSES_API_KEY)
