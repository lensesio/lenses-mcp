# 🌊🔍 Lenses MCP Server 🔎🌊

This is the MCP (Model Context Protocol) server for [Lenses](https://lenses.io/), a self-service DataOps tool for engineers building real-time applications with different flavours of Apache Kafka across multiple clusters. Explore, transform and join data in topics from different clusters using SQL, without the need for an additional database. 

Try this with the free [Lenses Community Edition](https://lenses.io/community-edition/) (restricted by number of users and enterprise features, e.g. OAuth). *Requires Lenses v6+*.

## Table of Contents

- [1. Install uv and Python](#1-install-uv-and-python)
- [2. Configure Environment Variables](#2-configure-environment-variables)
- [3. Add Lenses API Key](#3-add-lenses-api-key)
- [4. Install Dependencies and Run the Server](#4-install-dependencies-and-run-the-server)
- [5. Optional Context7 MCP Server](#5-optional-context7-mcp-server)


## 1. Install uv and Python

We use `uv` for dependency management and project setup. If you don't have `uv` installed, follow the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).

This project has been built using *Python 3.12* and to make sure Python is correctly installed, run the following command to check the version.

```bash
uv run python --version
```

## 2. Configure Environment Variables

Copy the example environment file.

```bash
cp .env.example .env
```

Open `.env` and fill in the required values such as your Lenses instance details and Lenses API key.

## 3. Add Lenses API Key

Create a Lenses API key by creating an [IAM Service Account](https://docs.lenses.io/latest/user-guide/iam/service-accounts). Add the API  key to `.env` with the variable name, `LENSES_API_KEY`.

## 4. Install Dependencies and Run the Server

Use `uv` to create a virtual environment, install the project dependencies in it and then run the MCP server with the FastMCP CLI using the default stdio transport.
```bash
uv sync
uv run src/lenses_mcp/server.py
```

To run as a remote server, use the http transport.
```bash
uv run fastmcp run src/lenses_mcp/server.py --transport=http --port=8000
```

To run in Claude Desktop, Gemini CLI, Cursor, etc. use the following JSON configuration.
```json
{
  "mcpServers": {
    "Lenses.io": {
      "command": "uv",
      "args": [
        "run",
        "--project", "<ABSOLUTE_PATH_TO_THIS_REPO>",
        "--with", "fastmcp",
        "fastmcp",
        "run",
        "<ABSOLUTE_PATH_TO_THIS_REPO>/src/lenses_mcp/server.py"
      ],
      "env": {
        "LENSES_API_KEY": "<YOUR_LENSES_API_KEY>"
      },
      "transport": "stdio"
    }
  }
}
```
Note: Some clients may require the absolute path to `uv` in the command.

## 5. Optional Context7 MCP Server

Lenses documentation is available on [Context7](https://context7.com/websites/lenses_io). It is optional but highly recommended to use the [Context7 MCP Server](https://github.com/upstash/context7) and adjust your prompts with `use context7` to ensure the documentation available to the LLM is up to date.
