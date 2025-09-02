from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional

from common.api_client import api_client

"""
Topics / Datasets operations.
"""

# ======================
# KAFKA TOPIC OPERATIONS
# ======================

def register_topics(mcp: FastMCP):

    @mcp.tool()
    async def list_topics(environment: str) -> List[Dict[str, Any]]:
        """
        Retrieve information about all topics.
        
        Args:
            environment: The environment name.
        
        Returns:
            List of all topics with detailed information.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_topic(environment: str, topic_name: str) -> Dict[str, Any]:
        """
        Retrieve information about a specific topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            Detailed topic information including partitions, consumers, config, etc.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_topic_partitions(environment: str, topic_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve partition details for a given topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            List of partition details with leader, replicas, etc.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}/partitions"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_topic_partitions_v2(environment: str, topic_name: str) -> Dict[str, Any]:
        """
        Retrieve detailed partition information including messages and bytes (v2 endpoint).
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            Partition details with message counts, bytes, and JMX timestamp.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v2/topics/{topic_name}/partitions"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def create_topic_simple(
        environment: str,
        topic_name: str,
        partitions: int = 1,
        replication: int = 1,
        configs: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Creates a new Kafka topic with simple configuration.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic to create.
            partitions: Number of partitions (default: 1).
            replication: Replication factor (default: 1).
            configs: Additional topic configurations.
        
        Returns:
            Success message with topic name.
        """
        payload = {
            "topicName": topic_name,
            "partitions": partitions,
            "replication": replication
        }
        
        if configs:
            payload["configs"] = configs
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics"
        result = await api_client._make_request("POST", endpoint, payload)
        return result

    @mcp.tool()
    async def create_topic_advanced(
        environment: str,
        name: str,
        partitions: int = 1,
        replication: int = 1,
        configs: Optional[Dict[str, str]] = None,
        key_format: Optional[str] = None,
        key_schema: Optional[str] = None,
        value_format: Optional[str] = None,
        value_schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a new Kafka topic with advanced format and schema configuration.
        
        Args:
            environment: The environment name.
            name: Topic name.
            partitions: Number of partitions (default: 1).
            replication: Replication factor (default: 1).
            configs: Topic configurations.
            key_format: Key format (AVRO, JSON, CSV, XML, INT, LONG, STRING, BYTES, etc.).
            key_schema: Key schema (required for AVRO, JSON, CSV, XML).
            value_format: Value format.
            value_schema: Value schema.
        
        Returns:
            Creation result.
        """
        payload = {
            "name": name,
            "partitions": partitions,
            "replication": replication
        }
        
        if configs:
            payload["configs"] = configs
        
        if key_format or value_format:
            format_config = {}
            if key_format:
                format_config["key"] = {"format": key_format}
                if key_schema:
                    format_config["key"]["schema"] = key_schema
            if value_format:
                format_config["value"] = {"format": value_format}
                if value_schema:
                    format_config["value"]["schema"] = value_schema
            payload["format"] = format_config
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/kafka/topic"
        return await api_client._make_request("POST", endpoint, payload)

    @mcp.tool()
    async def delete_topic(environment: str, topic_name: str) -> str:
        """
        Delete a Kafka topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic to delete.
        
        Returns:
            Success message.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}"
        return await api_client._make_request("DELETE", endpoint)

    @mcp.tool()
    async def update_topic_config(
        environment: str, 
        topic_name: str, 
        configs: List[Dict[str, str]]
    ) -> str:
        """
        Update topic configuration.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
            configs: List of config key-value pairs [{"key": "retention.ms", "value": "86400000"}].
        
        Returns:
            Success message.
        """
        payload = {"configs": configs}
        endpoint = f"/api/v1/environments/{environment}/proxy/api/configs/topics/{topic_name}"
        return await api_client._make_request("PUT", endpoint, payload)

    @mcp.tool()
    async def get_topic_broker_configs(environment: str, topic_name: str) -> List[Dict[str, Any]]:
        """
        Get broker configurations for a topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            List of broker configuration details.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}/brokerConfigs"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def add_topic_partitions(
        environment: str, 
        topic_name: str, 
        partitions: int
    ) -> Dict[str, Any]:
        """
        Add partitions to an existing topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
            partitions: New total number of partitions.
        
        Returns:
            Updated partition count.
        """
        payload = {"partitions": partitions}
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/kafka/topics/{topic_name}/partitions"
        return await api_client._make_request("PUT", endpoint, payload)

    @mcp.tool()
    async def resend_message(
        environment: str, 
        topic_name: str, 
        partition: int, 
        offset: int
    ) -> Dict[str, Any]:
        """
        Resend a Kafka message.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
            partition: Kafka partition number.
            offset: Kafka offset.
        
        Returns:
            Resend operation result with partition and offset.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}/{partition}/{offset}/resend"
        return await api_client._make_request("PUT", endpoint)

    @mcp.tool()
    async def delete_message(
        environment: str, 
        topic_name: str, 
        partition: int, 
        offset: int
    ) -> str:
        """
        Delete a Kafka message.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
            partition: Kafka partition number.
            offset: Kafka offset.
        
        Returns:
            Success message.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/topics/{topic_name}/{partition}/{offset}"
        return await api_client._make_request("DELETE", endpoint)

    # =========================
    # TOPIC METADATA OPERATIONS
    # =========================

    @mcp.tool()
    async def list_topic_metadata(environment: str) -> List[Dict[str, Any]]:
        """
        List all topic metadata.
        
        Args:
            environment: The environment name.
        
        Returns:
            List of topic metadata including schemas and descriptions.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/metadata/topics"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_topic_metadata(environment: str, topic_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific topic.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            Topic metadata including schema information and tags.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/metadata/topics/{topic_name}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def create_topic_metadata(
        environment: str,
        topic_name: str,
        key_type: Optional[str] = None,
        value_type: Optional[str] = None,
        key_schema: Optional[str] = None,
        key_schema_version: Optional[int] = None,
        key_schema_inlined: Optional[str] = None,
        value_schema: Optional[str] = None,
        value_schema_version: Optional[int] = None,
        value_schema_inlined: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        additional_info: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create or update topic metadata.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
            key_type: Key data type.
            value_type: Value data type.
            key_schema: Key schema reference.
            key_schema_version: Key schema version.
            key_schema_inlined: Inlined key schema.
            value_schema: Value schema reference.
            value_schema_version: Value schema version.
            value_schema_inlined: Inlined value schema.
            description: Topic description.
            tags: List of tags.
            additional_info: Additional metadata information.
        
        Returns:
            Creation result.
        """
        payload = {"topicName": topic_name}
        
        if key_type:
            payload["keyType"] = key_type
        if value_type:
            payload["valueType"] = value_type
        if key_schema:
            payload["keySchema"] = key_schema
        if key_schema_version:
            payload["keySchemaVersion"] = key_schema_version
        if key_schema_inlined:
            payload["keySchemaInlined"] = key_schema_inlined
        if value_schema:
            payload["valueSchema"] = value_schema
        if value_schema_version:
            payload["valueSchemaVersion"] = value_schema_version
        if value_schema_inlined:
            payload["valueSchemaInlined"] = value_schema_inlined
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags
        if additional_info is not None:
            payload["additionalInfo"] = additional_info
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/metadata/topics"
        return await api_client._make_request("POST", endpoint, payload)

    @mcp.tool()
    async def delete_topic_metadata(environment: str, topic_name: str) -> Dict[str, Any]:
        """
        Delete topic metadata.
        
        Args:
            environment: The environment name.
            topic_name: Name of the topic.
        
        Returns:
            Success confirmation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/metadata/topics/{topic_name}"
        return await api_client._make_request("DELETE", endpoint)

    # ========================
    # KAFKA DATASET OPERATIONS
    # ========================

    @mcp.tool()
    async def list_datasets(
        environment: str,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        connections: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        sort_field: Optional[str] = None,
        sort_order: str = "asc",
        include_system: bool = False,
        search_fields: bool = True,
        schema_format: Optional[str] = None,
        has_records: Optional[bool] = None,
        is_compacted: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a paginated list of datasets (topics and other data sources).
        
        Args:
            environment: The environment name.
            page: Page number (default: 1).
            page_size: Items per page (default: 25).
            search: Search keyword for dataset, fields and description.
            connections: List of connection names to filter by.
            tags: List of tag names to filter by.
            sort_field: Field to sort results by.
            sort_order: Sorting order - "asc" or "desc" (default: "asc").
            include_system: Include system entities (default: False).
            search_fields: Search field names/documentation (default: True).
            schema_format: Schema format filter for SchemaRegistrySubject.
            has_records: Filter based on whether dataset has records.
            is_compacted: Filter based on compacted status (Kafka only).
        
        Returns:
            Paginated list of datasets with source types.
        """
        params = {
            "page": page,
            "pageSize": page_size,
            "sortOrder": sort_order,
            "includeSystemEntities": include_system,
            "searchFields": search_fields
        }
        
        if search:
            params["search"] = search
        if connections:
            params["connections"] = connections
        if tags:
            params["tags"] = tags
        if sort_field:
            params["sortField"] = sort_field
        if schema_format:
            params["schemaFormat"] = schema_format
        if has_records is not None:
            params["hasRecords"] = has_records
        if is_compacted is not None:
            params["isCompacted"] = is_compacted
        
        # Build query string
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_params.append(f"{key}={item}")
            else:
                query_params.append(f"{key}={value}")
        
        query_string = "&".join(query_params)
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/datasets?{query_string}"
        
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def get_dataset(environment: str, connection: str, dataset: str) -> Dict[str, Any]:
        """
        Get a single dataset by connection/name.
        
        Args:
            environment: The environment name.
            connection: The connection name (e.g., "kafka").
            dataset: The dataset name.
        
        Returns:
            Dataset details including fields, policies, permissions, and metadata.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/datasets/{connection}/{dataset}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def set_dataset_description(
        environment: str, 
        connection: str, 
        dataset_name: str, 
        description: str
    ) -> Dict[str, Any]:
        """
        Sets a dataset description.
        
        Args:
            environment: The environment name.
            connection: The connection name (e.g., "kafka").
            dataset_name: The dataset name.
            description: The description to set.
        
        Returns:
            Success confirmation.
        """
        if not description.strip():
            raise ValueError("Description cannot be blank")
        
        payload = {"description": description}
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/datasets/{connection}/{dataset_name}/description"
        
        return await api_client._make_request("PUT", endpoint, payload)

    @mcp.tool()
    async def add_dataset_tags(
        environment: str, 
        connection: str, 
        dataset_name: str, 
        tags: List[str]
    ) -> Dict[str, Any]:
        """
        Add one or more tags to a dataset.
        
        Args:
            environment: The environment name.
            connection: The connection name (e.g., "kafka").
            dataset_name: The dataset name.
            tags: List of tag names to add.
        
        Returns:
            Success confirmation.
        """
        payload = {
            "tags": [{"name": tag} for tag in tags]
        }
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/datasets/{connection}/{dataset_name}/tags"
        return await api_client._make_request("PUT", endpoint, payload)

    @mcp.tool()
    async def get_dataset_message_metrics(environment: str, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get ranged metrics for a dataset's messages.
        
        Args:
            environment: The environment name.
            entity_name: The dataset's entity name.
        
        Returns:
            List of message metrics with date and message count.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/datasets/kafka/{entity_name}/messages/metrics"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def bulk_delete_datasets(environment: str, dataset_ids: List[str]) -> Dict[str, Any]:
        """
        Deletes multiple datasets at once.
        
        Args:
            environment: The environment name.
            dataset_ids: List of dataset IDs (e.g., ["kafka://topic1", "kafka://topic2"]).
        
        Returns:
            Bulk operation results showing success/failure for each dataset.
        """
        payload = {
            "items": [{"id": dataset_id} for dataset_id in dataset_ids]
        }
        
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/bulk/datasets/delete"
        return await api_client._make_request("POST", endpoint, payload)
