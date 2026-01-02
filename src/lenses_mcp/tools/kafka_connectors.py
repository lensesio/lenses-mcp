from clients.http_client import api_client
from fastmcp import FastMCP
from models.kafka_connectors import (
    CreateKafkaConnectorInput,
    CreateKafkaConnectorOutput,
    DeleteKafkaConnectorInput,
    DeleteKafkaConnectorOutput,
    GetKafkaConnectorTargetDefinitionInput,
    GetKafkaConnectorTargetDefinitionOutput,
    ListKafkaConnectorsInput,
    ListKafkaConnectorsOutput,
    RestartKafkaConnectorTaskInput,
    RestartKafkaConnectorTaskOutput,
    SetActionOnKafkaConnectorInput,
    SetActionOnKafkaConnectorOutput,
    ValidateConnectorConfigurationInput,
    ValidateConnectorConfigurationOutput,
)

"""
Registers all Kafka Connector operations with the MCP server.
"""
def register_kafka_connectors(mcp: FastMCP):

    # ==========================
    # KAFKA CONNECTOR OPERATIONS
    # ==========================

    @mcp.tool()
    async def list_kafka_connectors(input: ListKafkaConnectorsInput) -> ListKafkaConnectorsOutput:
        """
        Retrieves a list of all Kafka connectors.
        
        Args:
            input: The input containing environment name and optional cluster/class filters.
        
        Returns:
            ListKafkaConnectorsOutput containing all connectors with their details.
        """
        params = {}
        if input.cluster:
            params["cluster"] = input.cluster
        if input.class_name:
            params["className"] = input.class_name
        
        # Build query string
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_params.append(f"{key}={item}")
            else:
                query_params.append(f"{key}={value}")
        
        query_string = "&".join(query_params) if query_params else ""
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/connectors"
        if query_string:
            endpoint += f"?{query_string}"
        
        result = await api_client._make_request("GET", endpoint)
        return ListKafkaConnectorsOutput(item=result)

    @mcp.tool()
    async def get_kafka_connector_target_definition(
        input: GetKafkaConnectorTargetDefinitionInput
    ) -> GetKafkaConnectorTargetDefinitionOutput:
        """
        Fetches the current target definition for a Kafka connector.
        
        Args:
            input: The input containing environment name, connect cluster name, and connector name.
        
        Returns:
            GetKafkaConnectorTargetDefinitionOutput containing the connector definition as a YAML string.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/resource/kafka/connect/{input.connect_cluster_name}/connector/{input.connector_name}"
        result = await api_client._make_request("GET", endpoint)
        return GetKafkaConnectorTargetDefinitionOutput(result=str(result))

    @mcp.tool()
    async def create_kafka_connector(input: CreateKafkaConnectorInput) -> CreateKafkaConnectorOutput:
        """
        Creates a new Kafka connector.
        
        Args:
            input: The input containing environment name, connector name, cluster, and configuration.
        
        Returns:
            CreateKafkaConnectorOutput containing the created connector object.
        """
        payload = {
            "name": input.name,
            "cluster": input.cluster,
            "configuration": input.configuration
        }
        
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/connectors"
        result = await api_client._make_request("POST", endpoint, payload)
        return CreateKafkaConnectorOutput(result=result)

    @mcp.tool()
    async def set_action_on_kafka_connector(
        input: SetActionOnKafkaConnectorInput
    ) -> SetActionOnKafkaConnectorOutput:
        """
        Controls a Kafka connector (start, stop, restart, pause, resume).
        
        Args:
            input: The input containing environment name, cluster, connector name, and action.
        
        Returns:
            SetActionOnKafkaConnectorOutput containing the result of the control operation.
        """
        # Action is already validated by Pydantic Literal type
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/clusters/{input.cluster}/connectors/{input.connector}/{input.action}"
        result = await api_client._make_request("PUT", endpoint)
        return SetActionOnKafkaConnectorOutput(result=result)

    @mcp.tool()
    async def restart_kafka_connector_task(
        input: RestartKafkaConnectorTaskInput
    ) -> RestartKafkaConnectorTaskOutput:
        """
        Restarts a specific task of a Kafka connector.
        
        Args:
            input: The input containing environment name, cluster, connector name, and task ID.
        
        Returns:
            RestartKafkaConnectorTaskOutput containing the result of the task restart operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/clusters/{input.cluster}/connectors/{input.connector}/tasks/{input.task_id}/restart"
        result = await api_client._make_request("PUT", endpoint)
        return RestartKafkaConnectorTaskOutput(result=result)

    @mcp.tool()
    async def delete_kafka_connector(input: DeleteKafkaConnectorInput) -> DeleteKafkaConnectorOutput:
        """
        Deletes a Kafka connector.
        
        Args:
            input: The input containing environment name, cluster, and connector name.
        
        Returns:
            DeleteKafkaConnectorOutput containing the result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/clusters/{input.cluster}/connectors/{input.connector}"
        result = await api_client._make_request("DELETE", endpoint)
        return DeleteKafkaConnectorOutput(result=result)

    @mcp.tool()
    async def validate_connector_configuration(
        input: ValidateConnectorConfigurationInput
    ) -> ValidateConnectorConfigurationOutput:
        """
        Validates a Kafka connector configuration.
        
        Args:
            input: The input containing environment name, connector name, cluster, and configuration.
        
        Returns:
            ValidateConnectorConfigurationOutput containing validation results and any errors.
        """
        payload = {
            "name": input.name,
            "cluster": input.cluster,
            "configuration": input.configuration
        }
        
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/kafka-connect/validate"
        result = await api_client._make_request("POST", endpoint, payload)
        return ValidateConnectorConfigurationOutput(result=result)

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
