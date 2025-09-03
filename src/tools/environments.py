from fastmcp import FastMCP
from typing import Any, Dict, List, Optional

from api_client import api_client


"""
Registers all environment-related tools with the MCP server.
"""
def register_environments(mcp: FastMCP):

    @mcp.tool()
    async def list_environments() -> List[Dict[str, Any]]:
        """
        Lists all Lenses environments.
        
        Returns:
            A list containing all environments with their details including status, metrics, and metadata.
        """
        result = await api_client._make_request("GET", "/api/v1/environments")
        return result.get("items", [])

    @mcp.tool()
    async def get_environment(name: str) -> Dict[str, Any]:
        """
        Retrieves a single Lenses environment by name.
        
        Args:
            name: The name of the environment to retrieve.
        
        Returns:
            A dictionary containing the environment's details including status, metrics, and metadata.
        """
        if not name:
            raise ValueError("Environment name is required")
        
        return await api_client._make_request("GET", f"/api/v1/environments/{name}")

    @mcp.tool()
    async def create_environment(
        name: str,
        display_name: Optional[str] = None,
        tier: str = "development",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new Lenses environment.
        
        Args:
            name: The name of the new environment. Must be a valid resource name (lowercase alphanumeric or hyphens, max 63 chars).
            display_name: The display name of the environment. If not provided, 'name' will be used.
            tier: The environment tier. Options: "development", "staging", "production". Default: "development".
            metadata: Additional metadata as key-value pairs.
        
        Returns:
            The created environment object including the agent_key for setup.
        """
        if not name:
            raise ValueError("Environment name is required")
        
        # Validate name format
        if not name.replace('-', '').isalnum() or name.startswith('-') or name.endswith('-') or len(name) > 63:
            raise ValueError("Name must be lowercase alphanumeric or hyphens, not start/end with hyphens, max 63 chars")
        
        valid_tiers = ["development", "staging", "production"]
        if tier not in valid_tiers:
            raise ValueError(f"Tier must be one of: {', '.join(valid_tiers)}")
        
        payload = {
            "name": name,
            "tier": tier
        }
        
        if display_name:
            payload["display_name"] = display_name
        
        if metadata:
            payload["metadata"] = metadata
        
        return await api_client._make_request("POST", "/api/v1/environments", payload)

    @mcp.tool()
    async def update_environment(
        name: str,
        display_name: Optional[str] = None,
        tier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Updates an existing Lenses environment.
        
        Args:
            name: The name of the environment to update.
            display_name: New display name for the environment.
            tier: New tier for the environment. Options: "development", "staging", "production".
            metadata: New metadata as key-value pairs.
        
        Returns:
            The updated environment object.
        """
        if not name:
            raise ValueError("Environment name is required")
        
        payload = {}
        
        if display_name is not None:
            payload["display_name"] = display_name
        
        if tier is not None:
            valid_tiers = ["development", "staging", "production"]
            if tier not in valid_tiers:
                raise ValueError(f"Tier must be one of: {', '.join(valid_tiers)}")
            payload["tier"] = tier
        
        if metadata is not None:
            payload["metadata"] = metadata
        
        if not payload:
            raise ValueError("At least one field (display_name, tier, or metadata) must be provided for update")
        
        return await api_client._make_request("PATCH", f"/api/v1/environments/{name}", payload)

    @mcp.tool()
    async def delete_environment(name: str) -> Dict[str, Any]:
        """
        Deletes a Lenses environment.
        
        Args:
            name: The name of the environment to delete.
        
        Returns:
            Success confirmation message.
        """
        if not name:
            raise ValueError("Environment name is required")
        
        return await api_client._make_request("DELETE", f"/api/v1/environments/{name}")

    @mcp.tool()
    async def get_environment_metrics(name: str) -> Dict[str, Any]:
        """
        Retrieves metrics for a specific Lenses environment.
        
        Args:
            name: The name of the environment.
        
        Returns:
            Environment metrics including Kafka, data, apps, and connect statistics.
        """
        env = await get_environment(name)
        
        if "status" not in env or "agent" not in env["status"]:
            return {"error": "No metrics available - agent not connected"}
        
        return {
            "environment": name,
            "agent_connected": env["status"]["agent_connected"],
            "last_updated": env["status"]["agent"]["updated_at"],
            "roundtrip_duration": env["status"]["agent"]["roundtrip_duration"],
            "agent_info": env["status"]["agent"]["agent"],
            "metrics": env["status"]["agent"]["metrics"]
        }

    @mcp.tool()
    async def list_environment_names() -> List[str]:
        """
        Returns a simple list of all environment names.
        
        Returns:
            A list of environment names.
        """
        environments = await list_environments()
        return [env["name"] for env in environments]

    @mcp.tool()
    async def check_environment_health(name: str) -> Dict[str, Any]:
        """
        Checks the health status of a Lenses environment.
        
        Args:
            name: The name of the environment to check.
        
        Returns:
            Health status information including agent connection and any issues.
        """
        env = await get_environment(name)
        
        health_status = {
            "environment": name,
            "healthy": False,
            "agent_connected": False,
            "issues": []
        }
        
        if "status" in env:
            health_status["agent_connected"] = env["status"].get("agent_connected", False)
            
            if env["status"]["agent_connected"] and "agent" in env["status"]:
                agent_data = env["status"]["agent"]
                metrics = agent_data.get("metrics", {})
                
                # Check for issues
                if "other" in metrics and metrics["other"].get("num_issues", 0) > 0:
                    health_status["issues"].append(f"Found {metrics['other']['num_issues']} issues")
                
                # Basic health check
                health_status["healthy"] = (
                    health_status["agent_connected"] and 
                    len(health_status["issues"]) == 0
                )
                
                # Add summary metrics
                health_status["summary"] = {
                    "kafka_brokers": metrics.get("kafka", {}).get("num_brokers", 0),
                    "topics": metrics.get("data", {}).get("num_topics", 0),
                    "consumers": metrics.get("apps", {}).get("num_consumers", 0),
                    "connectors": metrics.get("connect", {}).get("num_connectors", 0)
                }
        
        return health_status
