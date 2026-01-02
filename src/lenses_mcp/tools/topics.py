from clients.http_client import api_client
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from models.topics import (
    AddTopicPartitionsInput,
    AddTopicPartitionsOutput,
    CreateTopicInput,
    CreateTopicOutput,
    CreateTopicWithSchemaInput,
    CreateTopicWithSchemaOutput,
    GetTopicBrokerConfigsInput,
    GetTopicBrokerConfigsOutput,
    GetTopicInput,
    GetTopicOutput,
    GetTopicPartitionsInput,
    GetTopicPartitionsOutput,
    ListTopicsInput,
    ListTopicsOutput,
    ResendMessageInput,
    ResendMessageOutput,
    UpdateTopicConfigInput,
    UpdateTopicConfigOutput,
    GetTopicMetadataInput,
    GetTopicMetadataOutput,
    ListTopicMetadataInput,
    ListTopicMetadataOutput,
    UpdateTopicMetadataInput,
    UpdateTopicMetadataOutput,
    GetDatasetInput,
    GetDatasetOutput,
    GetDatasetMessageMetricsInput,
    GetDatasetMessageMetricsOutput,
    ListDatasetsInput,
    ListDatasetsOutput,
    UpdateDatasetTopicDescriptionInput,
    UpdateDatasetTopicDescriptionOutput,
    UpdateDatasetTopicTagsInput,
    UpdateDatasetTopicTagsOutput,
    TopicConfigItem,
)

"""
Registers all topic and dataset operations with the MCP server.
"""
def register_topics(mcp: FastMCP):

    # ================
    # TOPIC OPERATIONS
    # ================
    
    @mcp.tool()
    async def list_topics(input: ListTopicsInput) -> ListTopicsOutput:
        """
        Retrieve information about all topics.
        
        Args:
            input: The input containing the environment name.
        
        Returns:
            ListTopicsOutput containing a list of all topics with detailed information.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/topics"
        results = await api_client._make_request("GET", endpoint)
        return ListTopicsOutput(items=results)

    @mcp.tool()
    async def get_topic(input: GetTopicInput) -> GetTopicOutput:
        """
        Retrieve information about a specific topic.
        
        Args:
            input: The input containing environment name and topic name.
        
        Returns:
            GetTopicOutput containing detailed topic information including partitions, consumers, config, etc.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/topics/{input.topic_name}"
        result = await api_client._make_request("GET", endpoint)
        return GetTopicOutput(item=result)

    @mcp.tool()
    async def get_topic_partitions(input: GetTopicPartitionsInput) -> GetTopicPartitionsOutput:
        """
        Retrieve detailed partition information including messages and bytes (v2 endpoint).
        
        Args:
            input: The input containing environment name and topic name.
        
        Returns:
            GetTopicPartitionsOutput containing partition details with message counts, bytes, and JMX timestamp.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v2/topics/{input.topic_name}/partitions"
        result = await api_client._make_request("GET", endpoint)
        return GetTopicPartitionsOutput(item=result)

    @mcp.tool()
    async def create_topic(input: CreateTopicInput) -> CreateTopicOutput:
        """
        Creates a new Kafka topic with optional configuration.
        
        Args:
            input: The input containing environment name, topic name, partitions, replication, and optional configs.
        
        Returns:
            CreateTopicOutput containing the topic creation result.
        """
        payload = {
            "topicName": input.topic_name,
            "partitions": input.partitions,
            "replication": input.replication,
            "configs": input.configs if input.configs else {}
        }
        
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/topics"
        try:
            result = await api_client._make_request("POST", endpoint, payload)
            return CreateTopicOutput(result=str(result))
        except Exception as e:
            raise ToolError(f"Topic creation failed: {e}")
    
    @mcp.tool()
    async def create_topic_with_schema(input: CreateTopicWithSchemaInput) -> CreateTopicWithSchemaOutput:
        """
        Creates a new Kafka topic with optional format and schema configuration.
        
        Args:
            input: The input containing environment name, topic name, partitions, replication, configs, and optional format/schema configuration.
        
        Returns:
            CreateTopicWithSchemaOutput containing the topic creation result with schema information.
        """
        payload = {
            "name": input.name,
            "partitions": input.partitions,
            "replication": input.replication,
            "configs": input.configs if input.configs else {}
        }
        
        if input.key_format or input.value_format:
            format_config = {}
            if input.key_format:
                format_config["key"] = {"format": input.key_format}
                if input.key_schema:
                    format_config["key"]["schema"] = input.key_schema
            if input.value_format:
                format_config["value"] = {"format": input.value_format}
                if input.value_schema:
                    format_config["value"]["schema"] = input.value_schema
            payload["format"] = format_config
        
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/kafka/topic"
        try:
            result = await api_client._make_request("POST", endpoint, payload)
            return CreateTopicWithSchemaOutput(result=result)
        except Exception as e:
            raise ToolError(f"Topic creation failed: {e}")

    @mcp.tool()
    async def update_topic_config(input: UpdateTopicConfigInput) -> UpdateTopicConfigOutput:
        """
        Update topic configuration.
        
        Args:
            input: The input containing environment name, topic name, and list of config key-value pairs.
        
        Returns:
            UpdateTopicConfigOutput containing the success message.
        """
        # Convert Pydantic models to dict format expected by API
        configs = [{"key": item.key, "value": item.value} for item in input.configs]
        payload = {"configs": configs}
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/configs/topics/{input.topic_name}"
        result = await api_client._make_request("PUT", endpoint, payload)
        return UpdateTopicConfigOutput(result=str(result))

    @mcp.tool()
    async def get_topic_broker_configs(input: GetTopicBrokerConfigsInput) -> GetTopicBrokerConfigsOutput:
        """
        Get broker configurations for a topic.
        
        Args:
            input: The input containing environment name and topic name.
        
        Returns:
            GetTopicBrokerConfigsOutput containing a list of broker configuration details.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/topics/{input.topic_name}/brokerConfigs"
        results = await api_client._make_request("GET", endpoint)
        return GetTopicBrokerConfigsOutput(items=results)

    @mcp.tool()
    async def add_topic_partitions(input: AddTopicPartitionsInput) -> AddTopicPartitionsOutput:
        """
        Add partitions to an existing topic.
        
        Args:
            input: The input containing environment name, topic name, and new total number of partitions.
        
        Returns:
            AddTopicPartitionsOutput containing the updated partition count.
        """
        payload = {"partitions": input.partitions}
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/kafka/topics/{input.topic_name}/partitions"
        result = await api_client._make_request("PUT", endpoint, payload)
        return AddTopicPartitionsOutput(result=result)

    @mcp.tool()
    async def resend_message(input: ResendMessageInput) -> ResendMessageOutput:
        """
        Resend a Kafka message.
        
        Args:
            input: The input containing environment name, topic name, partition number, and offset.
        
        Returns:
            ResendMessageOutput containing the resend operation result with partition and offset.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/topics/{input.topic_name}/{input.partition}/{input.offset}/resend"
        result = await api_client._make_request("PUT", endpoint)
        return ResendMessageOutput(result=result)

    # =========================
    # TOPIC METADATA OPERATIONS
    # =========================

    @mcp.tool()
    async def list_topic_metadata(input: ListTopicMetadataInput) -> ListTopicMetadataOutput:
        """
        List all topic metadata.
        
        Args:
            input: The input containing the environment name.
        
        Returns:
            ListTopicMetadataOutput containing a list of topic metadata including schemas and descriptions.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/metadata/topics"
        results = await api_client._make_request("GET", endpoint)
        return ListTopicMetadataOutput(items=results)

    @mcp.tool()
    async def get_topic_metadata(input: GetTopicMetadataInput) -> GetTopicMetadataOutput:
        """
        Get metadata for a specific topic.
        
        Args:
            input: The input containing environment name and topic name.
        
        Returns:
            GetTopicMetadataOutput containing topic metadata including schema information and tags.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/metadata/topics/{input.topic_name}"
        result = await api_client._make_request("GET", endpoint)
        return GetTopicMetadataOutput(item=result)

    @mcp.tool()
    async def update_topic_metadata(input: UpdateTopicMetadataInput) -> UpdateTopicMetadataOutput:
        """
        Update topic metadata. The required parameters are: topicName, keyType and valueType.
        When updating tags, it is not a list of strings. 
        It is a list of objects with parameter 'name', e.g. [{'name':'tag1'},{'name':'tag2'}]
        
        Args:
            input: The input containing environment name and metadata dictionary with topicName, keyType, valueType, etc.
        
        Returns:
            UpdateTopicMetadataOutput containing the success message.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/metadata/topics"
        result = await api_client._make_request("POST", endpoint, input.metadata)
        return UpdateTopicMetadataOutput(result=str(result))
    
    # ========================
    # KAFKA DATASET OPERATIONS
    # ========================

    @mcp.tool()
    async def list_datasets(input: ListDatasetsInput) -> ListDatasetsOutput:
        """
        Retrieves a paginated list of datasets (topics and other data sources).
        
        Args:
            input: The input containing environment name and pagination/filter parameters.
        
        Returns:
            ListDatasetsOutput containing a paginated list of datasets with source types.
        """
        params = {
            "page": input.page,
            "pageSize": input.page_size,
            "sortOrder": input.sort_order,
            "includeSystemEntities": input.include_system,
            "searchFields": input.search_fields
        }
        
        if input.search:
            params["search"] = input.search
        if input.connections:
            params["connections"] = input.connections
        if input.tags:
            params["tags"] = input.tags
        if input.sort_field:
            params["sortField"] = input.sort_field
        if input.schema_format:
            params["schemaFormat"] = input.schema_format
        if input.has_records is not None:
            params["hasRecords"] = input.has_records
        if input.is_compacted is not None:
            params["isCompacted"] = input.is_compacted
        
        # Build query string
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_params.append(f"{key}={item}")
            else:
                query_params.append(f"{key}={value}")
        
        query_string = "&".join(query_params)
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/datasets?{query_string}"
        
        result = await api_client._make_request("GET", endpoint)
        return ListDatasetsOutput(item=result)

    @mcp.tool()
    async def get_dataset(input: GetDatasetInput) -> GetDatasetOutput:
        """
        Get a single dataset by connection/name.
        
        Args:
            input: The input containing environment name, connection name, and dataset name.
        
        Returns:
            GetDatasetOutput containing dataset details including fields, policies, permissions, and metadata.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/datasets/{input.connection}/{input.dataset}"
        result = await api_client._make_request("GET", endpoint)
        return GetDatasetOutput(item=result)

    @mcp.tool()
    async def get_dataset_message_metrics(input: GetDatasetMessageMetricsInput) -> GetDatasetMessageMetricsOutput:
        """
        Get ranged metrics for a dataset's messages.
        
        Args:
            input: The input containing environment name and entity name.
        
        Returns:
            GetDatasetMessageMetricsOutput containing a list of message metrics with date and message count.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/datasets/kafka/{input.entity_name}/messages/metrics"
        results = await api_client._make_request("GET", endpoint)
        return GetDatasetMessageMetricsOutput(metrics=results)
    
    @mcp.tool()
    async def update_dataset_topic_description(input: UpdateDatasetTopicDescriptionInput) -> UpdateDatasetTopicDescriptionOutput:
        """
        Update topic description (in metadata).
        
        Args:
            input: The input containing environment name, topic name, and optional description.
        
        Returns:
            UpdateDatasetTopicDescriptionOutput containing the success message.
        """
        # The description cannot be an empty string so if it is, replace with a null value
        description_payload = {"description": input.description if input.description else None}

        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/datasets/kafka/{input.topic_name}/description"

        result = await api_client._make_request("PUT", endpoint, description_payload)
        return UpdateDatasetTopicDescriptionOutput(result=result)
    
    @mcp.tool()
    async def update_dataset_topic_tags(input: UpdateDatasetTopicTagsInput) -> UpdateDatasetTopicTagsOutput:
        """
        Update topic tags (in metadata).
        
        Args:
            input: The input containing environment name, topic name, and list of tag names.
        
        Returns:
            UpdateDatasetTopicTagsOutput containing the success message.
        """
        tags_payload = {
            "tags": [{"name": tag_name} for tag_name in input.tags]
        }

        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/v1/datasets/kafka/{input.topic_name}/tags"
        result = await api_client._make_request("PUT", endpoint, tags_payload)
        return UpdateDatasetTopicTagsOutput(result=result)
