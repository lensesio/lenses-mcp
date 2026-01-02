"""
Pydantic models for environment-related tool inputs and outputs.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.base import (
    BaseInputModel,
    BaseOutputModel,
    EnvironmentName,
    ListOutput,
    SingleItemOutput,
)


class GetEnvironmentInput(BaseInputModel):
    """Input model for the get_environment tool."""
    
    name: EnvironmentName


class CreateEnvironmentInput(BaseInputModel):
    """Input model for the create_environment tool."""
    
    name: str = Field(
        ...,
        description="The name of the new environment. Must be a valid resource name (lowercase alphanumeric or hyphens, max 63 chars).",
        min_length=1,
        max_length=63,
        examples=["my-environment", "prod-cluster"]
    )
    
    display_name: Optional[str] = Field(
        None,
        description="The display name of the environment. If not provided, 'name' will be used.",
        examples=["My Environment", "Production Cluster"]
    )
    
    tier: Literal["development", "staging", "production"] = Field(
        "development",
        description="The environment tier. Options: 'development', 'staging', 'production'. Default: 'development'.",
        examples=["development", "staging", "production"]
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata as key-value pairs.",
        examples=[{"team": "data-engineering", "region": "us-east-1"}]
    )
    
    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that the name follows the required format: lowercase alphanumeric or hyphens, not start/end with hyphens."""
        # Note: min_length=1 and max_length=63 are handled by Field constraints
        # This validator handles the format requirements only
        if not v.replace('-', '').isalnum():
            raise ValueError("Name must contain only lowercase alphanumeric characters or hyphens")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Name must not start or end with hyphens")
        return v


class CheckEnvironmentHealthInput(BaseInputModel):
    """Input model for the check_environment_health tool."""
    
    name: EnvironmentName


# Output type aliases using generic models
ListEnvironmentsOutput = ListOutput  # items: list of environments
GetEnvironmentOutput = SingleItemOutput  # item: environment details
CreateEnvironmentOutput = SingleItemOutput  # item: created environment with agent_key


class EnvironmentHealthSummary(BaseModel):
    """Summary metrics for environment health."""
    
    model_config = ConfigDict(extra="allow")
    
    kafka_brokers: int = Field(
        0,
        description="Number of Kafka brokers in the environment.",
        ge=0
    )
    
    topics: int = Field(
        0,
        description="Number of topics in the environment.",
        ge=0
    )
    
    consumers: int = Field(
        0,
        description="Number of consumers in the environment.",
        ge=0
    )
    
    connectors: int = Field(
        0,
        description="Number of connectors in the environment.",
        ge=0
    )


class CheckEnvironmentHealthOutput(BaseOutputModel):
    """Output model for the check_environment_health tool."""
    
    environment: str = Field(
        ...,
        description="The name of the environment that was checked.",
        examples=["production", "staging"]
    )
    
    healthy: bool = Field(
        ...,
        description="Whether the environment is healthy (agent connected and no issues).",
        examples=[True, False]
    )
    
    agent_connected: bool = Field(
        ...,
        description="Whether the agent is connected to the environment.",
        examples=[True, False]
    )
    
    issues: List[str] = Field(
        default_factory=list,
        description="List of issues found in the environment.",
        examples=[["Found 2 issues"], []]
    )
    
    summary: Optional[EnvironmentHealthSummary] = Field(
        None,
        description="Summary metrics including kafka_brokers, topics, consumers, and connectors."
    )

