"""
Pydantic models for SQL Processor and deployment-related tool inputs and outputs.
"""
from typing import Any, Dict, List, Optional

from pydantic import Field

from models.base import (
    BaseInputModel,
    ClusterName,
    DictOutput,
    EnvironmentMixin,
    K8sNamespace,
    K8sPodName,
    ResourceName,
    SingleItemOutput,
    SqlProcessorId,
    StringOutput,
)


# ========================
# SQL PROCESSOR OPERATIONS
# ========================

class ListSqlProcessorsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the list_sql_processors tool."""
    pass


class GetSqlProcessorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_sql_processor tool."""
    
    sql_processor_id: SqlProcessorId


class CreateSqlProcessorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the create_sql_processor tool."""
    
    name: ResourceName
    
    sql: str = Field(
        ...,
        description="The SQL query/statement for the processor.",
        min_length=1,
        examples=["SELECT * FROM input_topic WHERE amount > 100"]
    )
    
    deployment: Optional[Dict[str, Any]] = Field(
        None,
        description="Deployment configuration including mode, runners, cluster, namespace, etc. "
                   "Use {mode: 'IN_PROC'} for local in-process mode when no deployment targets available. "
                   "Use {mode: 'KUBERNETES', details: {runners: 1, cluster: 'incluster', namespace: 'default'}} for K8s.",
        examples=[
            {"mode": "IN_PROC"},
            {"mode": "KUBERNETES", "details": {"runners": 1, "cluster": "incluster", "namespace": "default"}}
        ]
    )
    
    sql_processor_id: Optional[str] = Field(
        None,
        description="Optional processor ID. If not provided, will be auto-generated.",
        examples=["my-custom-id"]
    )
    
    description: Optional[str] = Field(
        None,
        description="Optional description of the processor.",
        examples=["Transforms user events for analytics"]
    )
    
    tags: Optional[List[str]] = Field(
        None,
        description="Optional list of tags for the processor.",
        examples=[["production", "analytics"], ["development"]]
    )


class DeleteSqlProcessorInput(EnvironmentMixin, BaseInputModel):
    """Input model for the delete_sql_processor tool."""
    
    sql_processor_id: SqlProcessorId


# =====================
# DEPLOYMENT OPERATIONS
# =====================

class GetDeploymentTargetsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_deployment_targets tool."""
    pass


class GetPodLogsInput(EnvironmentMixin, BaseInputModel):
    """Input model for the get_pod_logs tool."""
    
    cluster: ClusterName
    namespace: K8sNamespace
    pod: K8sPodName


# ============
# OUTPUT TYPE ALIASES
# ============

# SQL Processor operations - using generic outputs
ListSqlProcessorsOutput = SingleItemOutput  # item: dict with list of processors
GetSqlProcessorOutput = SingleItemOutput  # item: processor details
CreateSqlProcessorOutput = DictOutput  # result: created processor
DeleteSqlProcessorOutput = StringOutput  # result: success message

# Deployment operations - using generic outputs
GetDeploymentTargetsOutput = SingleItemOutput  # item: deployment targets
GetPodLogsOutput = StringOutput  # result: log content

