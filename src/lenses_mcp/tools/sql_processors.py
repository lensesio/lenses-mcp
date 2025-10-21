from typing import Any, Dict, List, Optional

from clients.http_client import api_client
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

"""
Registers all SQL Processor operations with the MCP server.
"""
def register_sql_processors(mcp: FastMCP):

    # ========================
    # SQL PROCESSOR OPERATIONS
    # ========================

    @mcp.tool()
    async def list_sql_processors(environment: str) -> Dict[str, Any]:
        """
        Retrieves all SQL processor details.
        
        Args:
            environment: The environment name.
        
        Returns:
            A dictionary containing a list of all SQL processors with their details.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v2/streams"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_sql_processor(environment: str, sql_processor_id: str) -> Dict[str, Any]:
        """
        Retrieves a single SQL processor by ID.
        
        Args:
            environment: The environment name.
            sql_processor_id: SQL processor unique identifier.
        
        Returns:
            Detailed SQL processor information including application, metadata, and deployment status.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v2/streams/{sql_processor_id}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def create_sql_processor(
        environment: str,
        name: str,
        sql: str,
        deployment: Dict[str, Any] = None,
        sql_processor_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new SQL processor.
        
        Args:
            environment: The environment name.
            name: The name of the SQL processor.
            sql: The SQL query/statement for the processor.
            deployment: Deployment configuration including details like mode, runners, cluster, namespace, etc.
                If there are no available deployment targets (Kubernetes or Connect clusters), use 'in process' mode: {{mode: "IN_PROC"}}
            sql_processor_id: Optional processor ID. If not provided, will be auto-generated.
            description: Optional description of the processor.
            tags: Optional list of tags for the processor.
        
        Returns:
            The created SQL processor object with its ID.
        """
        payload = {
            "name": name,
            "sql": sql
        }
        
        if sql_processor_id:
            payload["processorId"] = sql_processor_id
        if description:
            payload["description"] = description
        if deployment:
            payload["deployment"] = deployment
        if tags:
            payload["tags"] = tags
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v2/streams"

        try:
            return await api_client._make_request("POST", endpoint, payload)
        except Exception as e:
            raise ToolError(f"SQL processor creation failed for reason: {e}")

    @mcp.tool()
    async def delete_sql_processor(environment: str, sql_processor_id: str) -> str:
        """
        Removes an existing SQL processor.
        
        Args:
            environment: The environment name.
            sql_processor_id: SQL processor unique identifier.
        
        Returns:
            Success message confirming the deletion.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/streams/{sql_processor_id}"
        return await api_client._make_request("DELETE", endpoint)

    # =====================
    # DEPLOYMENT OPERATIONS
    # =====================

    @mcp.tool()
    async def get_deployment_targets(environment: str) -> Dict[str, Any]:
        """
        Returns deployment information including available Kubernetes clusters and Connect clusters.
        
        Args:
            environment: The environment name.
        
        Returns:
            Dictionary containing available deployment targets (Kubernetes clusters and Connect clusters).
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/deployment/targets"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_pod_logs(
        environment: str, 
        cluster: str, 
        namespace: str, 
        pod: str
    ) -> str:
        """
        Returns the logs produced by a running Kubernetes Pod.
        
        Args:
            environment: The environment name.
            cluster: Pod's cluster name.
            namespace: Pod's namespace.
            pod: Pod's name.
        
        Returns:
            The logs content as a string.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/k8s/logs/{cluster}/{namespace}/{pod}/download"
        return await api_client._make_request("GET", endpoint)

    # =======
    # PROMPTS
    # =======

    @mcp.prompt()
    def list_running_sql_processors(environment: str) -> str:
        """List all running SQL processors in the environment"""
        return f"""
            Please list all SQL processors in the '{environment}' environment that are currently running.
            Include their status, deployment information, and any relevant metrics.
            """

    @mcp.prompt()
    def generate_create_sql_processor_prompt(name: str, sql: str, environment: str) -> str:
        """Create a SQL processor with the specified name and SQL query"""
        return f"""
            Please create a SQL processor named '{name}' in the '{environment}' environment
            with the following SQL query:
            
            {sql}
            
            The processor should be configured with appropriate deployment settings.
            Here is an example 'deployment' for Community Edition, which uses a local 'in process' mode: {{mode: "IN_PROC"}}
            It should be used when there are no available deployment targets (Kubernetes or Connect clusters) in the environment.
            Here is an example 'deployment' for Kubenetes: {{mode: "KUBERNETES", details: {{runners: 1, cluster: "incluster", namespace: "ai-agent"}}}}
            The settings can be determined for 'cluster' and 'namespace' with the get_deployment_targets tool call.
            """

    @mcp.prompt()
    def troubleshoot_sql_processor(sql_processor_id: str, environment: str) -> str:
        """Troubleshoot a specific SQL processor"""
        return f"""
            Please help troubleshoot the SQL processor with ID '{sql_processor_id}' in the '{environment}' environment.
            If the ID cannot be found, assume it is the SQL processor's name.
            Check its status, deployment configuration, and logs to identify any issues.
            If it has status 'RUNNING' then there are currently no issues.
            """
