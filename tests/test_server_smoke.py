"""Smoke tests — verify the MCP server boots and registers all tools/prompts."""

import os
import sys

import pytest

# The source uses bare imports (e.g., `from config import ...`), so we need
# the lenses_mcp package directory on sys.path for the server module to load.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

from fastmcp import Client
from server import mcp

# Expected tools registered across all modules
EXPECTED_TOOLS = [
    # environments
    "list_environments",
    "get_environment",
    "create_environment",
    "check_environment_health",
    # topics
    "list_topics",
    "get_topic",
    "get_topic_partitions",
    "create_topic",
    "create_topic_with_schema",
    "update_topic_config",
    "get_topic_broker_configs",
    "add_topic_partitions",
    "resend_message",
    "list_topic_metadata",
    "get_topic_metadata",
    "update_topic_metadata",
    "list_datasets",
    "get_dataset",
    "get_dataset_message_metrics",
    "update_dataset_topic_description",
    "update_dataset_topic_tags",
    # kafka connectors
    "list_kafka_connectors",
    "get_kafka_connector_target_definition",
    "create_kafka_connector",
    "set_action_on_kafka_connector",
    "restart_kafka_connector_task",
    "delete_kafka_connector",
    "validate_connector_configuration",
    # consumer groups
    "list_consumer_groups",
    "list_consumer_groups_by_topic",
    "update_consumer_group_offsets",
    "delete_consumer_group_offsets",
    "update_consumer_group_topic_partition_offset",
    "delete_consumer_group_topic_partition_offset",
    "delete_consumer_group",
    # sql
    "execute_sql",
    # sql processors
    "list_sql_processors",
    "get_sql_processor",
    "create_sql_processor",
    "delete_sql_processor",
    "get_deployment_targets",
    "get_pod_logs",
]


@pytest.mark.asyncio
async def test_server_registers_all_tools():
    """All expected MCP tools are registered on the server."""
    # Use _list_tools() to bypass per-tool auth filtering; the STDIO test
    # client has no OAuth token so require_scopes hides every tool.
    tools = await mcp._list_tools()
    tool_names = {t.name for t in tools}

    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Missing tool: {expected}"


@pytest.mark.asyncio
async def test_server_registers_prompts():
    """Server registers at least one MCP prompt."""
    async with Client(mcp) as client:
        prompts = await client.list_prompts()
        assert len(prompts) > 0, "No prompts registered"

        prompt_names = {p.name for p in prompts}
        assert "generate_sql_query_for_task" in prompt_names


@pytest.mark.asyncio
async def test_tool_count_matches():
    """Tool count matches expected list — catches unregistered or extra tools."""
    tools = await mcp._list_tools()
    assert len(tools) == len(EXPECTED_TOOLS), (
        f"Expected {len(EXPECTED_TOOLS)} tools, got {len(tools)}. "
        f"Extra: {set(t.name for t in tools) - set(EXPECTED_TOOLS)}, "
        f"Missing: {set(EXPECTED_TOOLS) - set(t.name for t in tools)}"
    )
