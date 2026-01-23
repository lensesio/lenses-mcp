# 🌊🔍 Lenses MCP Server for Apache Kafka 🔎🌊

This is the [Lenses](https://lenses.io/) MCP (Model Context Protocol) server for Apache Kafka. Lenses offers a developer experience solution for engineers building real-time applications connected to Kafka. It's built for the enterprise and backed by a powerful IAM and governance model. 

With Lenses, you can find, explore, transform, integrate and replicate data across a multi-Kafka and vendor estate. Now, all this power is accessible through your AI Assistant or Agent via this Lenses MCP Server for Kafka.

[See it in action](https://www.youtube.com/watch?v=m8bSLyRnMAk) whilst walking through the streets of New York city!

Try it today with the free [Lenses Community Edition](https://lenses.io/community-edition/) (restricted by number of users and enterprise features, e.g. OAuth). Lenses CE comes with a pre-configured single-broker Kafka cluster, ideal for localhost development or for a demo. But feel free to connect to up to two of your own Kafka clusters and then talk-away to your Kafka and streaming data. 

## Table of Contents

- [1. Install uv and Python](#1-install-uv-and-python)
- [2. Configure Environment Variables](#2-configure-environment-variables)
- [3. Add Lenses API Key](#3-add-lenses-api-key)
- [4. Install Dependencies and Run the Server](#4-install-dependencies-and-run-the-server)
- [5. Optional Context7 MCP Server](#5-optional-context7-mcp-server)
- [6. Running with Docker](#6-running-with-docker)


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

## 6. Running with Docker

The Lenses MCP server is available as a Docker image at `lensesio/mcp`. You can run it with different transport modes depending on your use case.

### Quick Start

Run the server with stdio transport (default):
```bash
docker run \
   -e LENSES_API_KEY=<YOUR_API_KEY> \
   -e LENSES_URL=http://localhost:9991 \
   lensesio/mcp
```

Run the server with HTTP transport (listens on `http://0.0.0.0:8000/mcp`):
```bash
docker run -p 8000:8000 \
   -e LENSES_API_KEY=<YOUR_API_KEY> \
   -e LENSES_URL=http://localhost:9991 \
   -e TRANSPORT=http \
   lensesio/mcp
```

Run the server with SSE transport (listens on `http://0.0.0.0:8000/sse`):
```bash
docker run -p 8000:8000 \
   -e LENSES_API_KEY=<YOUR_API_KEY> \
   -e LENSES_URL=http://localhost:9991 \
   -e TRANSPORT=sse \
   lensesio/mcp
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LENSES_API_KEY` | Yes | - | Your Lenses API key (create via [IAM Service Account](https://docs.lenses.io/latest/user-guide/iam/service-accounts)) |
| `LENSES_URL` | No | `http://localhost:9991` | Lenses instance URL in format `[scheme]://[host]:[port]`. Use `https://` for secure connections (automatically uses `wss://` for WebSockets) |
| `TRANSPORT` | No | `stdio` | Transport mode: `stdio`, `http`, or `sse` |
| `PORT` | No | `8000` | Port to listen on (only used with `http` or `sse` transport) |

**Legacy environment variables** (for backward compatibility):
- `LENSES_API_HTTP_URL`, `LENSES_API_HTTP_PORT`
- `LENSES_API_WEBSOCKET_URL`, `LENSES_API_WEBSOCKET_PORT`

These are automatically derived from `LENSES_URL` but can be explicitly set to override.

### Transport Endpoints

- **stdio**: Standard input/output (no network endpoint)
- **http**: HTTP endpoint at `/mcp`
- **sse**: Server-Sent Events endpoint at `/sse`

### Building the Docker Image

To build the Docker image locally:

```bash
docker build -t lensesio/mcp .
```
