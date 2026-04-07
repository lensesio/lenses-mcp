# Tests

## Running Tests

```bash
# Quick run
uv run pytest -x -q

# With coverage
uv run pytest --cov=src --cov-report=term-missing -x -q

# Via Makefile
make test
make test-cov
```

## Test Structure

| File | What it tests |
|---|---|
| `test_config.py` | Configuration parsing — URL defaults, HTTPS/WSS derivation |
| `test_server_smoke.py` | Server smoke tests — verifies all MCP tools and prompts register correctly |

## Testing Approach

Tests use **FastMCP's in-memory client** (`Client(mcp)`) to connect directly to the server without network or subprocess overhead. This validates tool/prompt registration without requiring a running Lenses backend.

```python
from fastmcp import Client
from server import mcp

async with Client(mcp) as client:
    tools = await client.list_tools()
    result = await client.call_tool("tool_name", {"param": "value"})
```

## Adding New Tests

- Place test files in this directory with the `test_` prefix
- Use `pytest-asyncio` for async tests (`@pytest.mark.asyncio`)
- The `src/lenses_mcp` directory is on `sys.path` so you can import modules directly (e.g., `from server import mcp`)
- For tests that call tools requiring a Lenses backend, mock the `api_client` or `websocket_client` singletons
