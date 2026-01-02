"""
Pydantic models for topic and dataset-related tool inputs and outputs.
"""
from typing import Any, Dict, List, Literal, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.base import (
    BaseInputModel,
    ConnectionName,
    DatasetName,
    DictOutput,
    EntityName,
    EnvironmentMixin,
    ListOutput,
    MetricsListOutput,
    OffsetNumber,
    PartitionCount,
    PartitionNumber,
    ReplicationFactor,
    SingleItemOutput,
    StringOutput,
    TopicConfigs,
    TopicName,
)


# ================
# TOPIC OPERATIONS
# ================

class ListTopicsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_topics tool."""
    pass


class GetTopicInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_topic tool."""
    
    topic_name: TopicName


class GetTopicPartitionsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_topic_partitions tool."""
    
    topic_name: TopicName


class CreateTopicInput(EnvironmentMixin, BaseInputModel):
    """Input model for the create_topic tool."""
    
    topic_name: TopicName
    partitions: PartitionCount = 1
    replication: ReplicationFactor = 1
    configs: TopicConfigs = None


class TopicFormatConfig(BaseModel):
    """Format configuration for topic key or value."""
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    
    format: str = Field(
        ...,
        description="Format type (AVRO, JSON, CSV, XML, INT, LONG, STRING, BYTES, etc.).",
        examples=["AVRO", "JSON", "STRING"]
    )
    
    schema_def: Optional[str] = Field(
        None,
        description="Schema definition (required for AVRO, JSON, CSV, XML).",
        examples=['{"type": "string"}'],
        alias="schema"
    )


# Schema formats that require a schema definition
SCHEMA_REQUIRED_FORMATS: set[str] = {"AVRO", "JSON", "CSV", "XML"}


class CreateTopicWithSchemaInput(EnvironmentMixin, BaseInputModel):
    """Input model for the create_topic_with_schema tool."""
    
    name: TopicName
    partitions: PartitionCount = 1
    replication: ReplicationFactor = 1
    configs: TopicConfigs = None
    
    key_format: Optional[str] = Field(
        None,
        description="Key format (AVRO, JSON, CSV, XML, INT, LONG, STRING, BYTES, etc.).",
        examples=["AVRO", "JSON", "STRING"]
    )
    
    key_schema: Optional[str] = Field(
        None,
        description="Key schema (required for AVRO, JSON, CSV, XML).",
        examples=['{"type": "string"}']
    )
    
    value_format: Optional[str] = Field(
        None,
        description="Value format (AVRO, JSON, CSV, XML, INT, LONG, STRING, BYTES, etc.).",
        examples=["AVRO", "JSON", "STRING"]
    )
    
    value_schema: Optional[str] = Field(
        None,
        description="Value schema (required for AVRO, JSON, CSV, XML).",
        examples=['{"type": "record", "name": "User", "fields": []}']
    )
    
    @model_validator(mode='after')
    def validate_schema_requirements(self) -> Self:
        """Validate that schema is provided when format requires it."""
        if self.key_format and self.key_format.upper() in SCHEMA_REQUIRED_FORMATS:
            if not self.key_schema:
                raise ValueError(f"key_schema is required when key_format is {self.key_format}")
        if self.value_format and self.value_format.upper() in SCHEMA_REQUIRED_FORMATS:
            if not self.value_schema:
                raise ValueError(f"value_schema is required when value_format is {self.value_format}")
        return self


class TopicConfigItem(BaseModel):
    """A single topic configuration item."""
    
    key: str = Field(
        ...,
        description="Configuration key.",
        examples=["retention.ms", "compression.type"]
    )
    
    value: str = Field(
        ...,
        description="Configuration value.",
        examples=["86400000", "snappy"]
    )


class UpdateTopicConfigInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_topic_config tool."""
    
    topic_name: TopicName
    configs: List[TopicConfigItem] = Field(
        ...,
        description="List of config key-value pairs.",
        examples=[[{"key": "retention.ms", "value": "86400000"}]]
    )


class GetTopicBrokerConfigsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_topic_broker_configs tool."""
    
    topic_name: TopicName


class AddTopicPartitionsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the add_topic_partitions tool."""
    
    topic_name: TopicName
    partitions: PartitionCount


class ResendMessageInput(EnvironmentMixin, BaseInputModel):
    """Input model for the resend_message tool."""
    
    topic_name: TopicName
    partition: PartitionNumber
    offset: OffsetNumber


# =========================
# TOPIC METADATA OPERATIONS
# =========================

class ListTopicMetadataInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_topic_metadata tool."""
    pass


class GetTopicMetadataInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_topic_metadata tool."""
    
    topic_name: TopicName


class TopicMetadataTag(BaseModel):
    """A tag for topic metadata."""
    
    name: str = Field(
        ...,
        description="Tag name.",
        examples=["production", "user-data", "analytics"]
    )


class UpdateTopicMetadataInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_topic_metadata tool."""
    
    metadata: Dict[str, Any] = Field(
        ...,
        description="Metadata key-value pairs. Required parameters: topicName, keyType, valueType. "
                   "Tags should be a list of objects with 'name' parameter, e.g. [{'name':'tag1'},{'name':'tag2'}].",
        examples=[{
            "topicName": "my-topic",
            "keyType": "string",
            "valueType": "avro",
            "description": "User events topic",
            "tags": [{"name": "production"}, {"name": "user-data"}]
        }]
    )


# ========================
# KAFKA DATASET OPERATIONS
# ========================

class ListDatasetsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_datasets tool."""
    
    page: int = Field(
        1,
        description="Page number (default: 1).",
        ge=1,
        examples=[1, 2, 3]
    )
    
    page_size: int = Field(
        25,
        description="Items per page (default: 25).",
        ge=1,
        examples=[25, 50, 100]
    )
    
    search: Optional[str] = Field(
        None,
        description="Search keyword for dataset, fields and description.",
        examples=["user", "events", "analytics"]
    )
    
    connections: Optional[List[str]] = Field(
        None,
        description="List of connection names to filter by.",
        examples=[["kafka"], ["kafka", "postgres"]]
    )
    
    tags: Optional[List[str]] = Field(
        None,
        description="List of tag names to filter by.",
        examples=[["production"], ["production", "user-data"]]
    )
    
    sort_field: Optional[str] = Field(
        None,
        description="Field to sort results by.",
        examples=["name", "created_at"]
    )
    
    sort_order: Literal["asc", "desc"] = Field(
        "asc",
        description="Sorting order - 'asc' or 'desc' (default: 'asc').",
        examples=["asc", "desc"]
    )
    
    include_system: bool = Field(
        False,
        description="Include system entities (default: False).",
        examples=[False, True]
    )
    
    search_fields: bool = Field(
        True,
        description="Search field names/documentation (default: True).",
        examples=[True, False]
    )
    
    schema_format: Optional[str] = Field(
        None,
        description="Schema format filter for SchemaRegistrySubject.",
        examples=["AVRO", "JSON"]
    )
    
    has_records: Optional[bool] = Field(
        None,
        description="Filter based on whether dataset has records.",
        examples=[True, False]
    )
    
    is_compacted: Optional[bool] = Field(
        None,
        description="Filter based on compacted status (Kafka only).",
        examples=[True, False]
    )


class GetDatasetInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_dataset tool."""
    
    connection: ConnectionName
    dataset: DatasetName


class GetDatasetMessageMetricsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_dataset_message_metrics tool."""
    
    entity_name: EntityName


class UpdateDatasetTopicDescriptionInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_dataset_topic_description tool."""
    
    topic_name: TopicName
    description: Optional[str] = Field(
        None,
        description="The description of the topic. Cannot be an empty string.",
        examples=["User events topic for analytics", "Production data stream"]
    )


class UpdateDatasetTopicTagsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_dataset_topic_tags tool."""
    
    topic_name: TopicName
    tags: List[str] = Field(
        ...,
        description="List of tag names.",
        min_length=1,
        examples=[["production", "user-data"], ["analytics"]]
    )


# ============
# OUTPUT TYPE ALIASES
# These use generic output models from base.py for reduced boilerplate
# ============

# Topic operations - using generic outputs
ListTopicsOutput = ListOutput  # items: list of topics
GetTopicOutput = SingleItemOutput  # item: topic details
GetTopicPartitionsOutput = SingleItemOutput  # item: partition details
CreateTopicOutput = StringOutput  # result: success message
CreateTopicWithSchemaOutput = DictOutput  # result: creation result
UpdateTopicConfigOutput = StringOutput  # result: success message
GetTopicBrokerConfigsOutput = ListOutput  # items: broker configs
AddTopicPartitionsOutput = DictOutput  # result: partition update info
ResendMessageOutput = DictOutput  # result: resend info

# Metadata operations - using generic outputs
ListTopicMetadataOutput = ListOutput  # items: metadata list
GetTopicMetadataOutput = SingleItemOutput  # item: metadata
UpdateTopicMetadataOutput = StringOutput  # result: success message

# Dataset operations - using generic outputs
ListDatasetsOutput = SingleItemOutput  # item: paginated datasets (dict with items/total/page)
GetDatasetOutput = SingleItemOutput  # item: dataset details
GetDatasetMessageMetricsOutput = MetricsListOutput  # metrics: message metrics
UpdateDatasetTopicDescriptionOutput = DictOutput  # result: update status
UpdateDatasetTopicTagsOutput = DictOutput  # result: update status

