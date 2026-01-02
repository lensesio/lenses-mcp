from clients.http_client import api_client
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from models.sql_processors import (
    CreateSqlProcessorInput,
    CreateSqlProcessorOutput,
    DeleteSqlProcessorInput,
    DeleteSqlProcessorOutput,
    GetDeploymentTargetsInput,
    GetDeploymentTargetsOutput,
    GetPodLogsInput,
    GetPodLogsOutput,
    GetSqlProcessorInput,
    GetSqlProcessorOutput,
    ListSqlProcessorsInput,
    ListSqlProcessorsOutput,
)

"""
Registers all SQL Processor operations with the MCP server.
"""
def register_sql_processors(mcp: FastMCP):

    # ========================
    # SQL PROCESSOR OPERATIONS
    # ========================

    @mcp.tool()
    async def list_sql_processors(input: ListSqlProcessorsInput) -> ListSqlProcessorsOutput:
        """
        Retrieves all SQL processor details.
        
        Args:
            input: The input containing the environment name.
        
        Returns:
            ListSqlProcessorsOutput containing all SQL processors with their details.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v2/streams"
        result = await api_client._make_request("GET", endpoint)
        return ListSqlProcessorsOutput(item=result)

    @mcp.tool()
    async def get_sql_processor(input: GetSqlProcessorInput) -> GetSqlProcessorOutput:
        """
        Retrieves a single SQL processor by ID.
        
        Args:
            input: The input containing environment name and SQL processor ID.
        
        Returns:
            GetSqlProcessorOutput containing detailed SQL processor information including application, metadata, and deployment status.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v2/streams/{input.sql_processor_id}"
        result = await api_client._make_request("GET", endpoint)
        return GetSqlProcessorOutput(item=result)

    @mcp.tool()
    async def create_sql_processor(input: CreateSqlProcessorInput) -> CreateSqlProcessorOutput:
        """
        Creates a new SQL processor.
        
        Args:
            input: The input containing environment name, processor name, SQL query, and optional deployment/metadata settings.
        
        Returns:
            CreateSqlProcessorOutput containing the created SQL processor object with its ID.
        """
        payload = {
            "name": input.name,
            "sql": input.sql
        }
        
        if input.sql_processor_id:
            payload["processorId"] = input.sql_processor_id
        if input.description:
            payload["description"] = input.description
        if input.deployment:
            payload["deployment"] = input.deployment
        if input.tags:
            payload["tags"] = input.tags
        
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v2/streams"

        try:
            result = await api_client._make_request("POST", endpoint, payload)
            return CreateSqlProcessorOutput(result=result)
        except Exception as e:
            raise ToolError(f"SQL processor creation failed: {e}")

    @mcp.tool()
    async def delete_sql_processor(input: DeleteSqlProcessorInput) -> DeleteSqlProcessorOutput:
        """
        Removes an existing SQL processor.
        
        Args:
            input: The input containing environment name and SQL processor ID.
        
        Returns:
            DeleteSqlProcessorOutput containing success message confirming the deletion.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/streams/{input.sql_processor_id}"
        result = await api_client._make_request("DELETE", endpoint)
        return DeleteSqlProcessorOutput(result=str(result))

    # =====================
    # DEPLOYMENT OPERATIONS
    # =====================

    @mcp.tool()
    async def get_deployment_targets(input: GetDeploymentTargetsInput) -> GetDeploymentTargetsOutput:
        """
        Returns deployment information including available Kubernetes clusters and Connect clusters.
        
        Args:
            input: The input containing the environment name.
        
        Returns:
            GetDeploymentTargetsOutput containing available deployment targets (Kubernetes clusters and Connect clusters).
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/deployment/targets"
        result = await api_client._make_request("GET", endpoint)
        return GetDeploymentTargetsOutput(item=result)

    @mcp.tool()
    async def get_pod_logs(input: GetPodLogsInput) -> GetPodLogsOutput:
        """
        Returns the logs produced by a running Kubernetes Pod.
        
        Args:
            input: The input containing environment name, cluster, namespace, and pod name.
        
        Returns:
            GetPodLogsOutput containing the logs content as a string.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/k8s/logs/{input.cluster}/{input.namespace}/{input.pod}/download"
        result = await api_client._make_request("GET", endpoint)
        return GetPodLogsOutput(result=str(result))

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
