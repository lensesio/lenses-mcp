"""
Pydantic models for Kafka Consumer Group tool inputs and outputs.
"""
from typing import Any, Dict, List

from pydantic import Field

from models.base import (
    BaseInputModel,
    ConsumerGroupId,
    DictOutput,
    EnvironmentMixin,
    ListOutput,
    OffsetNumber,
    PartitionNumber,
    TopicName,
)


# ================================
# KAFKA CONSUMER GROUP OPERATIONS
# ================================

class ListConsumerGroupsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_consumer_groups tool."""
    pass


class ListConsumerGroupsByTopicInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_consumer_groups_by_topic tool."""
    
    topic: TopicName


class ConsumerGroupOffsetItem(BaseInputModel):
    """A single topic-partition offset item for consumer group operations."""
    
    topic: TopicName
    partition: PartitionNumber
    offset: OffsetNumber


class TopicPartitionItem(BaseInputModel):
    """A single topic-partition item (without offset) for delete operations."""
    
    topic: TopicName
    partition: PartitionNumber


class UpdateConsumerGroupOffsetsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_consumer_group_offsets tool."""
    
    group_id: ConsumerGroupId
    
    offsets: List[Dict[str, Any]] = Field(
        ...,
        description="A list of topic-partition offset objects.",
        min_length=1,
        examples=[[{"topic": "my-topic", "partition": 0, "offset": 100}]]
    )


class DeleteConsumerGroupOffsetsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the delete_consumer_group_offsets tool."""
    
    group_id: ConsumerGroupId
    
    offsets: List[Dict[str, Any]] = Field(
        ...,
        description="A list of topic-partition objects to delete offsets for.",
        min_length=1,
        examples=[[{"topic": "my-topic", "partition": 0}]]
    )


class UpdateConsumerGroupTopicPartitionOffsetInput(EnvironmentMixin, BaseInputModel):
    """Input model for the update_consumer_group_topic_partition_offset tool."""
    
    group_id: ConsumerGroupId
    topic: TopicName
    partition: PartitionNumber
    offset: OffsetNumber


class DeleteConsumerGroupTopicPartitionOffsetInput(EnvironmentMixin, BaseInputModel):
    """Input model for the delete_consumer_group_topic_partition_offset tool."""
    
    group_id: ConsumerGroupId
    topic: TopicName
    partition: PartitionNumber


class DeleteConsumerGroupInput(EnvironmentMixin, BaseInputModel):
    """Input model for the delete_consumer_group tool."""
    
    group_id: ConsumerGroupId


# ============
# OUTPUT TYPE ALIASES
# ============

ListConsumerGroupsOutput = ListOutput  # items: list of consumer groups
ListConsumerGroupsByTopicOutput = ListOutput  # items: list of consumer groups
UpdateConsumerGroupOffsetsOutput = DictOutput  # result: update result
DeleteConsumerGroupOffsetsOutput = DictOutput  # result: delete result
UpdateConsumerGroupTopicPartitionOffsetOutput = DictOutput  # result: update result
DeleteConsumerGroupTopicPartitionOffsetOutput = DictOutput  # result: delete result
DeleteConsumerGroupOutput = DictOutput  # result: delete result

