from typing import Any, Literal

from clients.http_client import api_client
from config import oauth_required_scopes
from fastmcp import FastMCP

"""
Registers all Kafka consumer group operations with the MCP server.
"""


def register_kafka_consumer_groups(mcp: FastMCP):

    @mcp.tool(auth=oauth_required_scopes("read"))
    async def list_consumer_groups(environment: str) -> list[dict[str, Any]]:
        """
        Retrieve a list of all Kafka consumer groups.

        Args:
            environment: The environment name.

        Returns:
            A list of consumer group objects.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool(auth=oauth_required_scopes("read"))
    async def list_consumer_groups_by_topic(environment: str, topic: str) -> list[dict[str, Any]]:
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

    @mcp.tool(auth=oauth_required_scopes("write"))
    async def update_consumer_group_offsets(
        environment: str,
        group_id: str,
        topics: list[str],
        reset_to: Literal["start", "end", "timestamp"],
        target: str | None = None,
    ) -> dict[str, Any]:
        """
        Reset offsets for all partitions of one or more topics in a consumer group.

        The reset is applied to every partition of every listed topic. For
        per-partition control use `update_consumer_group_topic_partition_offset`.

        The consumer group must be inactive (no live members), otherwise Kafka
        rejects the offset commit.

        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            topics: One or more topic names to reset.
            reset_to: Where to reset offsets to: "start" (earliest), "end"
                (latest), or "timestamp" (the offset committed for each
                partition becomes the first record at or after `target`).
            target: RFC 3339 / ISO 8601 timestamp (e.g. "2026-04-28T10:00:00Z").
                Required when reset_to == "timestamp", ignored otherwise.

        Returns:
            The result of the update operation.
        """
        if reset_to == "timestamp" and not target:
            raise ValueError("`target` (RFC 3339 timestamp) is required when reset_to='timestamp'")

        payload: dict[str, Any] = {"type": reset_to, "topics": topics}
        if reset_to == "timestamp":
            payload["target"] = target

        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/offsets"
        return await api_client._make_request("PUT", endpoint, data=payload)

    @mcp.tool(auth=oauth_required_scopes("delete"))
    async def delete_consumer_group_offsets(environment: str, group_id: str, topics: list[str]) -> dict[str, Any]:
        """
        Delete the committed offsets for all partitions of one or more topics
        in a consumer group.

        For per-partition control use `delete_consumer_group_topic_partition_offset`.

        The consumer group must be inactive (no live members), otherwise Kafka
        rejects the deletion.

        Args:
            environment: The environment name.
            group_id: The ID of the consumer group.
            topics: One or more topic names whose committed offsets should be
                deleted from the group.

        Returns:
            The result of the delete operation.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/consumers/{group_id}/offsets/delete"
        return await api_client._make_request("POST", endpoint, data={"topics": topics})

    @mcp.tool(auth=oauth_required_scopes("write"))
    async def update_consumer_group_topic_partition_offset(
        environment: str, group_id: str, topic: str, partition: int, offset: int
    ) -> dict[str, Any]:
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
        endpoint = (
            f"/api/v1/environments/{environment}/proxy/api/consumers"
            f"/{group_id}/offsets/topics/{topic}/partitions/{partition}"
        )
        payload = {"type": "absolute", "offset": offset}
        return await api_client._make_request("PUT", endpoint, data=payload)

    @mcp.tool(auth=oauth_required_scopes("delete"))
    async def delete_consumer_group_topic_partition_offset(
        environment: str, group_id: str, topic: str, partition: int
    ) -> dict[str, Any]:
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
        endpoint = (
            f"/api/v1/environments/{environment}/proxy/api/consumers"
            f"/{group_id}/topics/{topic}/partitions/{partition}/offsets"
        )
        return await api_client._make_request("DELETE", endpoint)

    @mcp.tool(auth=oauth_required_scopes("delete"))
    async def delete_consumer_group(environment: str, group_id: str) -> dict[str, Any]:
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

    @mcp.prompt()
    def list_consumer_groups_for_topic(topic: str, environment: str) -> str:
        """List consumer groups for a specified topic in a specified environment"""
        return f"""
            Please list consumer groups for the '{topic}' topic in the '{environment}' environment
            """
