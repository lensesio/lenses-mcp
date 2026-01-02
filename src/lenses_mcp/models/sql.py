"""
Pydantic models for SQL-related tool inputs and outputs.
"""
from typing import Any, Dict, List

from pydantic import Field

from models.base import BaseInputModel, BaseOutputModel, EnvironmentMixin


class ExecuteSQLInput(EnvironmentMixin, BaseInputModel):
    """Input model for the execute_sql tool."""
    
    sql: str = Field(
        ...,
        description="The SQL statement/query to execute using the Lenses WebSocket API.",
        min_length=1,
        examples=["SELECT * FROM topics LIMIT 10"]
    )


class ExecuteSQLOutput(BaseOutputModel):
    """Output model for the execute_sql tool."""
    
    results: List[Dict[str, Any]] = Field(
        ...,
        description="A list of records representing the result of the SQL query. Each record contains the data returned by the query execution.",
        examples=[[{"column1": "value1", "column2": "value2"}]]
    )
