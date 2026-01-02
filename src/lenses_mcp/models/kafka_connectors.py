"""
Pydantic models for Kafka Connector tool inputs and outputs.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from models.base import (
    BaseInputModel,
    ClusterName,
    ConnectorName,
    DictOutput,
    EnvironmentMixin,
    SingleItemOutput,
    StringOutput,
)


# ==========================
# KAFKA CONNECTOR OPERATIONS
# ==========================

class ListKafkaConnectorsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_kafka_connectors tool."""
    
    cluster: Optional[List[str]] = Field(
        None,
        description="Optional list of cluster names to filter by.",
        examples=[["my-cluster"], ["cluster-1", "cluster-2"]]
    )
    
    class_name: Optional[List[str]] = Field(
        None,
        description="Optional list of connector class names to filter by.",
        examples=[["io.debezium.connector.mysql.MySqlConnector"]]
    )


class GetKafkaConnectorTargetDefinitionInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_kafka_connector_target_definition tool."""
    
    connect_cluster_name: ClusterName
    connector_name: ConnectorName


class CreateKafkaConnectorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the create_kafka_connector tool."""
    
    name: ConnectorName
    cluster: ClusterName
    
    configuration: Dict[str, Any] = Field(
        ...,
        description="The connector configuration as a dictionary.",
        examples=[{
            "connector.class": "io.debezium.connector.mysql.MySqlConnector",
            "tasks.max": "1",
            "database.hostname": "localhost"
        }]
    )


class SetActionOnKafkaConnectorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the set_action_on_kafka_connector tool."""
    
    cluster: ClusterName
    connector: ConnectorName
    
    action: Literal["start", "stop", "restart", "pause", "resume"] = Field(
        ...,
        description="The action to perform on the connector.",
        examples=["start", "stop", "restart", "pause", "resume"]
    )


class RestartKafkaConnectorTaskInput(EnvironmentMixin, BaseInputModel):
    """Input model for the restart_kafka_connector_task tool."""
    
    cluster: ClusterName
    connector: ConnectorName
    
    task_id: int = Field(
        ...,
        description="The task ID to restart.",
        ge=0,
        examples=[0, 1, 2]
    )


class DeleteKafkaConnectorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the delete_kafka_connector tool."""
    
    cluster: ClusterName
    connector: ConnectorName


class ValidateConnectorConfigurationInput(EnvironmentMixin, BaseInputModel):
    """Input model for the validate_connector_configuration tool."""
    
    name: ConnectorName
    cluster: ClusterName
    
    configuration: Dict[str, Any] = Field(
        ...,
        description="The connector configuration to validate.",
        examples=[{
            "connector.class": "io.debezium.connector.mysql.MySqlConnector",
            "tasks.max": "1"
        }]
    )


# ============
# OUTPUT TYPE ALIASES
# ============

ListKafkaConnectorsOutput = SingleItemOutput  # item: dict with connectors list
GetKafkaConnectorTargetDefinitionOutput = StringOutput  # result: YAML definition
CreateKafkaConnectorOutput = DictOutput  # result: created connector
SetActionOnKafkaConnectorOutput = DictOutput  # result: action result
RestartKafkaConnectorTaskOutput = DictOutput  # result: task restart result
DeleteKafkaConnectorOutput = DictOutput  # result: delete result
ValidateConnectorConfigurationOutput = DictOutput  # result: validation results

