"""
Base Pydantic models and mixins for shared functionality.

This module provides:
- Base model classes with consistent configuration
- Annotated type aliases for commonly reused fields (DRY principle)
- Mixin classes for shared field definitions
"""
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseInputModel(BaseModel):
    """Base class for all tool input models."""
    
    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_default=True,
    )


class BaseOutputModel(BaseModel):
    """Base class for all tool output models."""
    
    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        validate_default=True,
    )


# ===================
# Generic Output Models
# ===================

class DictOutput(BaseOutputModel):
    """Generic output for operations returning a dictionary result."""
    
    result: Dict[str, Any] = Field(
        ...,
        description="The operation result as a dictionary."
    )


class StringOutput(BaseOutputModel):
    """Generic output for operations returning a string result."""
    
    result: str = Field(
        ...,
        description="The operation result as a string message."
    )


class ListOutput(BaseOutputModel):
    """Generic output for operations returning a list of items."""
    
    items: List[Dict[str, Any]] = Field(
        ...,
        description="A list of items returned by the operation."
    )


class SingleItemOutput(BaseOutputModel):
    """Generic output for operations returning a single item."""
    
    item: Dict[str, Any] = Field(
        ...,
        description="A single item returned by the operation."
    )


class MetricsListOutput(BaseOutputModel):
    """Generic output for operations returning a list of metrics."""
    
    metrics: List[Dict[str, Any]] = Field(
        ...,
        description="A list of metrics returned by the operation."
    )


class EnvironmentMixin(BaseModel):
    """Mixin providing the common environment field used across many tools."""
    
    environment: str = Field(
        ...,
        description="The environment name where the operation will be performed.",
        min_length=1,
        examples=["production", "staging", "development"]
    )


# ===================
# Annotated Type Aliases for Reusable Field Definitions
# ===================

# Environment-related fields
EnvironmentName = Annotated[str, Field(
    ...,
    description="The name of the environment.",
    min_length=1,
    examples=["production", "staging", "development"]
)]

# Topic-related fields
TopicName = Annotated[str, Field(
    ...,
    description="Name of the topic.",
    min_length=1,
    examples=["my-topic", "user-events"]
)]

# Kafka-related fields
PartitionNumber = Annotated[int, Field(
    ...,
    description="Kafka partition number.",
    ge=0,
    examples=[0, 1, 2]
)]

OffsetNumber = Annotated[int, Field(
    ...,
    description="Kafka offset.",
    ge=0,
    examples=[0, 100, 1000]
)]

PartitionCount = Annotated[int, Field(
    ...,
    description="Number of partitions.",
    ge=1,
    examples=[1, 3, 6]
)]

ReplicationFactor = Annotated[int, Field(
    ...,
    description="Replication factor.",
    ge=1,
    examples=[1, 3]
)]

# Configuration fields
TopicConfigs = Annotated[Optional[Dict[str, str]], Field(
    None,
    description="Topic configurations as key-value pairs.",
    examples=[{"retention.ms": "86400000", "compression.type": "snappy"}]
)]

# Connection/Dataset fields  
ConnectionName = Annotated[str, Field(
    ...,
    description="The connection name (e.g., 'kafka').",
    min_length=1,
    examples=["kafka", "postgres"]
)]

DatasetName = Annotated[str, Field(
    ...,
    description="The dataset name.",
    min_length=1,
    examples=["my-topic", "users-table"]
)]

EntityName = Annotated[str, Field(
    ...,
    description="The entity name.",
    min_length=1,
    examples=["my-topic", "user-events"]
)]

# Kafka Connect fields
ClusterName = Annotated[str, Field(
    ...,
    description="The Kafka Connect cluster name.",
    min_length=1,
    examples=["my-connect-cluster", "production-cluster"]
)]

ConnectorName = Annotated[str, Field(
    ...,
    description="The Kafka connector name.",
    min_length=1,
    examples=["my-connector", "mysql-source"]
)]

# Consumer Group fields
ConsumerGroupId = Annotated[str, Field(
    ...,
    description="The ID of the consumer group.",
    min_length=1,
    examples=["my-consumer-group", "analytics-consumer"]
)]

# SQL Processor fields
SqlProcessorId = Annotated[str, Field(
    ...,
    description="SQL processor unique identifier.",
    min_length=1,
    examples=["my-processor", "processor-123"]
)]

# Kubernetes fields
K8sNamespace = Annotated[str, Field(
    ...,
    description="Kubernetes namespace.",
    min_length=1,
    examples=["default", "ai-agent", "lenses"]
)]

K8sPodName = Annotated[str, Field(
    ...,
    description="Kubernetes pod name.",
    min_length=1,
    examples=["my-processor-pod-abc123"]
)]

# Generic resource name (for connectors, processors, etc.)
ResourceName = Annotated[str, Field(
    ...,
    description="Resource name.",
    min_length=1,
    examples=["my-resource", "data-transform"]
)]

