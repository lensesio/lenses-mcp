from typing import Any, Dict, List, Optional

from clients.http_client import api_client
from fastmcp import FastMCP

"""
Registers all Kafka Connector operations with the MCP server.
"""
def register_kafka_connectors(mcp: FastMCP):

    # ==========================
    # KAFKA CONNECTOR OPERATIONS
    # ==========================

    @mcp.tool()
    async def list_kafka_connectors(
        environment: str,
        cluster: Optional[List[str]] = None,
        class_name: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all Kafka connectors.
        
        Args:
            environment: The environment name.
            cluster: Optional list of cluster names to filter by.
            class_name: Optional list of connector class names to filter by.
        
        Returns:
            A dictionary containing a list of all connectors with their details.
        """
        params = {}
        if cluster:
            params["cluster"] = cluster
        if class_name:
            params["className"] = class_name
        
        # Build query string
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_params.append(f"{key}={item}")
            else:
                query_params.append(f"{key}={value}")
        
        query_string = "&".join(query_params) if query_params else ""
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/connectors"
        if query_string:
            endpoint += f"?{query_string}"
        
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_kafka_connector_target_definition(
        environment: str, 
        connect_cluster_name: str, 
        connector_name: str
    ) -> str:
        """
        Fetches the current target definition for a Kafka connector.
        
        Args:
            environment: The environment name.
            connect_cluster_name: The connect cluster name.
            connector_name: The connector name.
        
        Returns:
            The connector definition as a YAML string.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/resource/kafka/connect/{connect_cluster_name}/connector/{connector_name}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def create_kafka_connector(
        environment: str,
        name: str,
        cluster: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates a new Kafka connector.
        
        Args:
            environment: The environment name.
            name: The name of the connector.
            cluster: The cluster name where the connector will be deployed.
            configuration: The connector configuration as a dictionary.
        
        Returns:
            The created connector object.
        """
        payload = {
            "name": name,
            "cluster": cluster,
            "configuration": configuration
        }
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/connectors"
        return await api_client._make_request("POST", endpoint, payload)

    @mcp.tool()
    async def set_action_on_kafka_connector(
        environment: str,
        cluster: str,
        connector: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Controls a Kafka connector (start, stop, restart, pause, resume).
        
        Args:
            environment: The environment name.
            cluster: The cluster name.
            connector: The connector name.
            action: The action to perform. Options: "start", "stop", "restart", "pause", "resume".
        
        Returns:
            The result of the control operation.
        """
        valid_actions = ["start", "stop", "restart", "pause", "resume"]
        if action not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/clusters/{cluster}/connectors/{connector}/{action}"
        return await api_client._make_request("PUT", endpoint)

    @mcp.tool()
    async def restart_kafka_connector_task(
        environment: str,
        cluster: str,
        connector: str,
        task_id: int
    ) -> Dict[str, Any]:
        """
        Restarts a specific task of a Kafka connector.
        
        Args:
            environment: The environment name.
            cluster: The cluster name.
            connector: The connector name.
            task_id: The task ID to restart.
        
        Returns:
            The result of the task restart operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/clusters/{cluster}/connectors/{connector}/tasks/{task_id}/restart"
        return await api_client._make_request("PUT", endpoint)

    @mcp.tool()
    async def delete_kafka_connector(
        environment: str,
        cluster: str,
        connector: str
    ) -> Dict[str, Any]:
        """
        Deletes a Kafka connector.
        
        Args:
            environment: The environment name.
            cluster: The cluster name.
            connector: The connector name.
        
        Returns:
            The result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/clusters/{cluster}/connectors/{connector}"
        return await api_client._make_request("DELETE", endpoint)

    @mcp.tool()
    async def validate_connector_configuration(
        environment: str,
        name: str,
        cluster: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates a Kafka connector configuration.
        
        Args:
            environment: The environment name.
            name: The name of the connector.
            cluster: The cluster name.
            configuration: The connector configuration to validate.
        
        Returns:
            Validation results including configuration details and any errors.
        """
        payload = {
            "name": name,
            "cluster": cluster,
            "configuration": configuration
        }
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/kafka-connect/validate"
        return await api_client._make_request("POST", endpoint, payload)

    # =======
    # PROMPTS
    # =======

    @mcp.prompt()
    def list_running_kafka_connectors(environment: str) -> str:
        """List all running Kafka connectors in the environment"""
        return f"""
            Please list all Kafka connectors in the '{environment}' environment that are currently running.
            Include their status, cluster information, and task details.
            """

    @mcp.prompt()
    def generate_create_kafka_connector_prompt(name: str, cluster: str, connector_class: str, environment: str) -> str:
        """Create a Kafka connector with the specified configuration"""
        return f"""
            Please create a Kafka connector named '{name}' in the '{environment}' environment
            on cluster '{cluster}' using connector class '{connector_class}'.
            
            The connector should be configured with appropriate settings for its type.
            """

    @mcp.prompt()
    def troubleshoot_kafka_connector(connector_name: str, environment: str) -> str:
        """Troubleshoot a specific Kafka connector"""
        return f"""
            Please help troubleshoot the Kafka connector '{connector_name}' in the '{environment}' environment.
            Check its status, task states, configuration, and any error messages to identify issues.
            If all tasks show 'RUNNING' status, then the connector is functioning properly.
            """

    @mcp.prompt()
    def validate_kafka_connector_config(name: str, cluster: str, environment: str) -> str:
        """Validate a Kafka connector configuration before deployment"""
        return f"""
            Please validate the configuration for connector '{name}' in the '{environment}' environment
            on cluster '{cluster}'. Check for any configuration errors or missing required parameters.
            """
