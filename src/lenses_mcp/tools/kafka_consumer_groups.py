from typing import List

from clients.http_client import api_client
from fastmcp import FastMCP
from models.kafka_consumer_groups import (
    DeleteConsumerGroupInput,
    DeleteConsumerGroupOffsetsInput,
    DeleteConsumerGroupOffsetsOutput,
    DeleteConsumerGroupOutput,
    DeleteConsumerGroupTopicPartitionOffsetInput,
    DeleteConsumerGroupTopicPartitionOffsetOutput,
    ListConsumerGroupsByTopicInput,
    ListConsumerGroupsByTopicOutput,
    ListConsumerGroupsInput,
    ListConsumerGroupsOutput,
    UpdateConsumerGroupOffsetsInput,
    UpdateConsumerGroupOffsetsOutput,
    UpdateConsumerGroupTopicPartitionOffsetInput,
    UpdateConsumerGroupTopicPartitionOffsetOutput,
)

"""
Registers all Kafka consumer group operations with the MCP server.
"""
def register_kafka_consumer_groups(mcp: FastMCP):

    @mcp.tool()
    async def list_consumer_groups(input: ListConsumerGroupsInput) -> ListConsumerGroupsOutput:
        """
        Retrieve a list of all Kafka consumer groups.
        
        Args:
            input: The input containing the environment name.
        
        Returns:
            ListConsumerGroupsOutput containing a list of consumer group objects.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers"
        result = await api_client._make_request("GET", endpoint)
        return ListConsumerGroupsOutput(items=result)

    @mcp.tool()
    async def list_consumer_groups_by_topic(
        input: ListConsumerGroupsByTopicInput
    ) -> ListConsumerGroupsByTopicOutput:
        """
        Retrieve a list of consumer groups by a specific topic.
        
        Args:
            input: The input containing environment name and topic name.
        
        Returns:
            ListConsumerGroupsByTopicOutput containing a list of consumer group objects.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.topic}"
        result = await api_client._make_request("GET", endpoint)
        return ListConsumerGroupsByTopicOutput(items=result)

    @mcp.tool()
    async def update_consumer_group_offsets(
        input: UpdateConsumerGroupOffsetsInput
    ) -> UpdateConsumerGroupOffsetsOutput:
        """
        Update the offset for a consumer group topic-partition tuples.
        
        Args:
            input: The input containing environment name, group ID, and offset list.
        
        Returns:
            UpdateConsumerGroupOffsetsOutput containing the result of the update operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.group_id}/offsets"
        result = await api_client._make_request("PUT", endpoint, json=input.offsets)
        return UpdateConsumerGroupOffsetsOutput(result=result)

    @mcp.tool()
    async def delete_consumer_group_offsets(
        input: DeleteConsumerGroupOffsetsInput
    ) -> DeleteConsumerGroupOffsetsOutput:
        """
        Delete offsets for a consumer group topic-partition tuples.
        
        Args:
            input: The input containing environment name, group ID, and offset list.
        
        Returns:
            DeleteConsumerGroupOffsetsOutput containing the result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.group_id}/offsets/delete"
        result = await api_client._make_request("POST", endpoint, json=input.offsets)
        return DeleteConsumerGroupOffsetsOutput(result=result)

    @mcp.tool()
    async def update_consumer_group_topic_partition_offset(
        input: UpdateConsumerGroupTopicPartitionOffsetInput
    ) -> UpdateConsumerGroupTopicPartitionOffsetOutput:
        """
        Update the offset for a topic-partition for a given group.
        
        Args:
            input: The input containing environment name, group ID, topic, partition, and offset.
        
        Returns:
            UpdateConsumerGroupTopicPartitionOffsetOutput containing the result of the update operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.group_id}/offsets/topics/{input.topic}/partitions/{input.partition}"
        payload = {"offset": input.offset}
        result = await api_client._make_request("PUT", endpoint, json=payload)
        return UpdateConsumerGroupTopicPartitionOffsetOutput(result=result)

    @mcp.tool()
    async def delete_consumer_group_topic_partition_offset(
        input: DeleteConsumerGroupTopicPartitionOffsetInput
    ) -> DeleteConsumerGroupTopicPartitionOffsetOutput:
        """
        Delete the offset for a topic-partition for a given group.
        
        Args:
            input: The input containing environment name, group ID, topic, and partition.
        
        Returns:
            DeleteConsumerGroupTopicPartitionOffsetOutput containing the result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.group_id}/topics/{input.topic}/partitions/{input.partition}/offsets"
        result = await api_client._make_request("DELETE", endpoint)
        return DeleteConsumerGroupTopicPartitionOffsetOutput(result=result)

    @mcp.tool()
    async def delete_consumer_group(input: DeleteConsumerGroupInput) -> DeleteConsumerGroupOutput:
        """
        Delete a consumer group.
        
        Args:
            input: The input containing environment name and group ID.
        
        Returns:
            DeleteConsumerGroupOutput containing the result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{input.environment}/proxy/api/consumers/{input.group_id}"
        result = await api_client._make_request("DELETE", endpoint)
        return DeleteConsumerGroupOutput(result=result)

    @mcp.prompt()
    def list_consumer_groups_for_topic(topic: str, environment: str) -> List[str]:
        """List consumer groups for a specified topic in a specified environment"""
        return f"""
            Please list consumer groups for the '{topic}' topic in the '{environment}' environment
            """
    