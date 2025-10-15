from typing import Any, Dict, List

from clients.websocket_client import websocket_client
from fastmcp import FastMCP

"""
Registers all SQL-related operations (such as SQL execution) with the MCP server.
"""
def register_sql(mcp: FastMCP):

    @mcp.tool()
    async def execute_sql(environment: str, sql: str) -> List[Dict[str, Any]]:
        """
        Executes SQL statements/queries using Lenses WebSocket API.

        Args:
            environment: The environment name.
            sql: The SQL statement/query to execute.
        
        Returns:
            A list of MessageRecord objects representing the result of the SQL query.
        """
        endpoint = f"/api/v1/environments/{environment}/proxy/api/ws/v2/sql/execute"
        return await websocket_client._make_request(endpoint=endpoint, sql=sql)

    # =======
    # PROMPTS
    # =======

    @mcp.prompt()
    def generate_sql_query_for_task(task: str) -> str:
        """Write a Lenses SQL query to achieve a task"""
        return f"""
            Task: {task}

            Please write a SQL query that accomplishes this task efficiently.

            Use these specific guidelines in addition to SQL best practices for performance:
            1. Use JOINs (INNER, LEFT) based on the data relationships where appropriate
            2. Use WHERE clauses to reduce the number of records where possible
            3. Use indentation to format the query for readability
            """
