from clients.http_client import api_client
from fastmcp import FastMCP
from models.environments import (
    CheckEnvironmentHealthInput,
    CheckEnvironmentHealthOutput,
    CreateEnvironmentInput,
    CreateEnvironmentOutput,
    EnvironmentHealthSummary,
    GetEnvironmentInput,
    GetEnvironmentOutput,
    ListEnvironmentsOutput,
)

"""
Registers all environment operations with the MCP server.
"""
def register_environments(mcp: FastMCP):

    @mcp.tool()
    async def list_environments() -> ListEnvironmentsOutput:
        """
        Lists all Lenses environments.
        
        Returns:
            ListEnvironmentsOutput containing a list of all environments with their details including status, metrics, and metadata.
        """
        result = await api_client._make_request("GET", "/api/v1/environments")
        return ListEnvironmentsOutput(items=result.get("items", []))

    @mcp.tool()
    async def get_environment(input: GetEnvironmentInput) -> GetEnvironmentOutput:
        """
        Retrieves a single Lenses environment by name.
        
        Args:
            input: The input containing the environment name to retrieve.
        
        Returns:
            GetEnvironmentOutput containing the environment's details including status, metrics, and metadata.
        """
        result = await api_client._make_request("GET", f"/api/v1/environments/{input.name}")
        return GetEnvironmentOutput(item=result)

    @mcp.tool()
    async def create_environment(input: CreateEnvironmentInput) -> CreateEnvironmentOutput:
        """
        Creates a new Lenses environment.
        
        Args:
            input: The input containing environment name, display_name, tier, and optional metadata.
        
        Returns:
            CreateEnvironmentOutput containing the created environment object including the agent_key for setup.
        """
        payload = {
            "name": input.name,
            "tier": input.tier
        }
        
        if input.display_name:
            payload["display_name"] = input.display_name
        
        if input.metadata:
            payload["metadata"] = input.metadata
        
        result = await api_client._make_request("POST", "/api/v1/environments", payload)
        return CreateEnvironmentOutput(item=result)

    @mcp.tool()
    async def check_environment_health(input: CheckEnvironmentHealthInput) -> CheckEnvironmentHealthOutput:
        """
        Checks the health status of a Lenses environment.
        
        Args:
            input: The input containing the environment name to check.
        
        Returns:
            CheckEnvironmentHealthOutput containing health status information including agent connection and any issues.
        """
        # Call get_environment with the input model
        env_input = GetEnvironmentInput(name=input.name)
        env_result = await get_environment(env_input)
        env = env_result.item
        
        health_status = CheckEnvironmentHealthOutput(
            environment=input.name,
            healthy=False,
            agent_connected=False,
            issues=[],
            summary=None
        )
        
        if "status" in env:
            health_status.agent_connected = env["status"].get("agent_connected", False)
            
            if env["status"]["agent_connected"] and "agent" in env["status"]:
                agent_data = env["status"]["agent"]
                metrics = agent_data.get("metrics", {})
                
                # Check for issues
                if "other" in metrics and metrics["other"].get("num_issues", 0) > 0:
                    health_status.issues.append(f"Found {metrics['other']['num_issues']} issues")
                
                # Basic health check
                health_status.healthy = (
                    health_status.agent_connected and 
                    len(health_status.issues) == 0
                )
                
                # Add summary metrics
                health_status.summary = EnvironmentHealthSummary(
                    kafka_brokers=metrics.get("kafka", {}).get("num_brokers", 0),
                    topics=metrics.get("data", {}).get("num_topics", 0),
                    consumers=metrics.get("apps", {}).get("num_consumers", 0),
                    connectors=metrics.get("connect", {}).get("num_connectors", 0)
                )
        
        return health_status

    # =======
    # PROMPTS
    # =======

    @mcp.prompt()
    def list_connected_environments() -> str:
        """List all connected environments"""
        return """
            Please list all environments where 'Agent Connected' has a value of 'True'
            """
