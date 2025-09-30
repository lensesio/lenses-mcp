from typing import Any, Dict, List

from clients.http_client import api_client
from fastmcp import FastMCP

"""
Kafka Consumer Groups operations.
"""
def register_kafka_consumer_groups(mcp: FastMCP):

    @mcp.tool()
    async def list_consumer_groups(environment: str) -> List[Dict[str, Any]]:
        """
        Retrieve a list of all Kafka consumer groups.
        
        Args:
            environment: The environment name.
        
        Returns:
            A list of consumer group objects.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def list_consumer_groups_by_topic(environment: str, topic: str) -> List[Dict[str, Any]]:
        """
        Retrieve a list of consumer groups by a specific topic.
        
        Args:
            environment: The environment name.
            topic: The name of the topic.
        
        Returns:
            A list of consumer group objects.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{topic}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool()
    async def update_consumer_group_offsets(
        environment: str, 
        group_id: str, 
        offsets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update the offset for a consumer group topic-partition tuples.
        
        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            offsets: A list of topic-partition offset objects.
        
        Returns:
            The result of the update operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/offsets"
        return await api_client._make_request("PUT", endpoint, json=offsets)

    @mcp.tool()
    async def delete_consumer_group_offsets(
        environment: str, 
        group_id: str, 
        offsets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Delete offsets for a consumer group topic-partition tuples.
        
        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            offsets: A list of topic-partition objects.
        
        Returns:
            The result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/offsets/delete"
        return await api_client._make_request("POST", endpoint, json=offsets)

    @mcp.tool()
    async def update_consumer_group_topic_partition_offset(
        environment: str, 
        group_id: str, 
        topic: str, 
        partition: int, 
        offset: int
    ) -> Dict[str, Any]:
        """
        Update the offset for a topic-partition for a given group.
        
        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            topic: The topic name.
            partition: The partition number.
            offset: The new offset value.
        
        Returns:
            The result of the update operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/offsets/topics/{topic}/partitions/{partition}"
        payload = {"offset": offset}
        return await api_client._make_request("PUT", endpoint, json=payload)

    @mcp.tool()
    async def delete_consumer_group_topic_partition_offset(
        environment: str, 
        group_id: str, 
        topic: str, 
        partition: int
    ) -> Dict[str, Any]:
        """
        Delete the offset for a topic-partition for a given group.
        
        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            topic: The topic name.
            partition: The partition number.
        
        Returns:
            The result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/topics/{topic}/partitions/{partition}/offsets"
        return await api_client._make_request("DELETE", endpoint)

    @mcp.tool()
    async def delete_consumer_group(environment: str, group_id: str) -> Dict[str, Any]:
        """
        Delete a consumer group.
        
        Args:
            environment: The environment name.
            group_id: The ID of the consumer group to delete.
        
        Returns:
            The result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}"
        return await api_client._make_request("DELETE", endpoint)
