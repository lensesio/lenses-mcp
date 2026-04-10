# 🌊🔍 Lenses MCP Server for Apache Kafka 🔎🌊

[![CI](https://github.com/lensesio/lenses-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/lensesio/lenses-mcp/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://python.org/)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.1.1-green)](https://gofastmcp.com/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green)](https://modelcontextprotocol.io/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

This is the [Lenses](https://lenses.io/) MCP (Model Context Protocol) server for Apache Kafka. Lenses offers a developer experience solution for engineers building real-time applications connected to Kafka. It's built for the enterprise and backed by a powerful IAM and governance model. 

With Lenses, you can find, explore, transform, integrate and replicate data across a multi-Kafka and vendor estate. Now, all this power is accessible through your AI Assistant or Agent via this Lenses MCP Server for Kafka.

[See it explained and in action](https://www.youtube.com/watch?v=m8bSLyRnMAk) whilst walking through the streets of New York city!

Try it today with the free [Lenses Community Edition](https://lenses.io/community-edition/) (restricted by number of users and enterprise features). Lenses CE comes with a pre-configured single broker Kafka cluster, ideal for local development or demonstration. Connect up to two of your own Kafka clusters and then use natural language to interact with your streaming data. 

## Table of Contents

- [1. Install uv and Python](#1-install-uv-and-python)
- [2. Configure Environment Variables](#2-configure-environment-variables)
- [3. Add Lenses API Key](#3-add-lenses-api-key)
- [4. Install Dependencies and Run the Server](#4-install-dependencies-and-run-the-server)
- [5. Optional Context7 MCP Server](#5-optional-context7-mcp-server)
- [6. Running with Docker](#6-running-with-docker)
- [7. OAuth 2.1 Authentication](#7-oauth-21-authentication)


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
| `LENSES_API_KEY` | Yes (unless using OAuth) | - | Your Lenses API key (create via [IAM Service Account](https://docs.lenses.io/latest/user-guide/iam/service-accounts)) |
| `LENSES_URL` | No | `http://localhost:9991` | Lenses instance URL in format `[scheme]://[host]:[port]`. Use `https://` for secure connections (automatically uses `wss://` for WebSockets) |
| `TRANSPORT` | No | `http` if `MCP_ADVERTISED_URL` is set, else `stdio` | Transport mode: `stdio`, `http`, or `sse` |
| `PORT` | No | `8000` | Port to listen on (only used with `http` or `sse` transport) |
| `MCP_ADVERTISED_URL` | Yes for OAuth | - | Public base URL of this MCP server as reachable by clients. Setting this turns OAuth on and defaults `TRANSPORT` to `http` (see [OAuth 2.1 Authentication](#7-oauth-21-authentication)) |
| `LENSES_ADVERTISED_URL` | No | `LENSES_URL` | Public Lenses HQ URL advertised to MCP clients for OAuth login. Override only in split-plane deployments where the MCP server reaches Lenses on an internal address |
| `MCP_SCOPES` | No | `read,write,delete` | Comma-separated OAuth scopes advertised in protected-resource metadata |
| `INTROSPECTION_URL` | No | Discovered from `LENSES_ADVERTISED_URL` metadata | Override for the RFC 7662 token introspection endpoint URL |
| `INTROSPECTION_CACHE_TTL` | No | `0` (disabled) | Cache TTL for introspection results in seconds |

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

## 7. OAuth 2.1 Authentication

When `MCP_ADVERTISED_URL` is set, the MCP server runs as an **OAuth 2.1 Protected Resource** with full [RFC 7662 Token Introspection](https://oauth.net/2/token-introspection/). This replaces the static `LENSES_API_KEY` approach with bearer-token authentication for HTTP transports, and also defaults `TRANSPORT` to `http`.

### How it works

The authentication flow involves three participants: the **MCP client**, the **authorization server** (Lenses HQ at `LENSES_ADVERTISED_URL`, which defaults to `LENSES_URL`), and this **MCP server** (the resource server).

```
MCP Client                    Auth Server                   MCP Server
    │                              │                             │
    │  1. GET /.well-known/        │                             │
    │     oauth-protected-resource │                             │
    │─────────────────────────────────────────────────────────►  │
    │  ◄── authorization_servers,                                │
    │      scopes_supported                                      │
    │                              │                             │
    │  2. POST /register (DCR)     │                             │
    │─────────────────────────────►│                             │
    │  ◄── client_id, secret       │                             │
    │                              │                             │
    │  3. /authorize + PKCE (S256) │                             │
    │─────────────────────────────►│                             │
    │  ◄── authorization_code      │                             │
    │                              │                             │
    │  4. POST /token              │                             │
    │─────────────────────────────►│                             │
    │  ◄── access_token            │                             │
    │                              │                             │
    │  5. MCP request + Bearer token                             │
    │─────────────────────────────────────────────────────────►  │
    │                              │  6. POST /oauth2/introspect │
    │                              │  ◄──────────────────────────│
    │                              │  ── active, scopes, exp ──► │
    │                              │                             │
    │  ◄── MCP response (or 401)                                 │
    │                              │                             │
```

**Steps 1–4** are handled by the MCP client and the authorization server. The MCP server is not involved.

**Steps 5–6** are where this server validates the token:

1. **Protected Resource Metadata** (RFC 9728) — `RemoteAuthProvider` serves `/.well-known/oauth-protected-resource/mcp` so clients can discover which authorization server to use and what scopes are available.

2. **Auto-Discovery** — On the first incoming request, the `DiscoveryTokenVerifier` lazily fetches `{LENSES_ADVERTISED_URL}/.well-known/oauth-authorization-server` to discover the `introspection_endpoint`. The endpoint URL can also be set explicitly via `INTROSPECTION_URL`.

3. **Token Introspection** (RFC 7662) — For each incoming bearer token, the verifier POSTs to the introspection endpoint (`/oauth2/introspect`) without client authentication. The authorization server responds with:
   - `active` — whether the token is valid
   - `scope` — granted scopes (e.g. `read write`)
   - `client_id` — the token's owner
   - `exp` — expiration timestamp

   Inactive or expired tokens are rejected before reaching the Lenses API.

4. **Token Forwarding** — Valid tokens are forwarded to the Lenses API via `Authorization: Bearer <token>` so Lenses can perform its own authorization checks.

### Authorization scopes

The server advertises three scopes in its protected-resource metadata:

| Scope | Description |
|-------|-------------|
| `read` | Read-only access to Lenses resources (topics, environments, connectors, etc.) |
| `write` | Create and update resources |
| `delete` | Delete resources |

Scopes are not enforced globally at the introspection level — a token with any subset of these scopes is accepted. Per-tool scope enforcement can be added using FastMCP's `require_scopes` decorator.

### Configuration

In a simple deployment, only two environment variables are required:

```bash
LENSES_URL=https://lenses.example.com
MCP_ADVERTISED_URL=http://localhost:8000
```

`TRANSPORT` defaults to `http` whenever `MCP_ADVERTISED_URL` is set, so you don't need to set it explicitly. `LENSES_ADVERTISED_URL` defaults to `LENSES_URL`, so you only need to set it in **split-plane deployments** where the MCP server reaches Lenses on an internal address but clients reach it on a public one:

```bash
# Split-plane: MCP server → Lenses over internal DNS,
# MCP clients → Lenses over the public URL
LENSES_URL=http://lenses-hq.internal:9991
LENSES_ADVERTISED_URL=https://lenses.example.com
MCP_ADVERTISED_URL=https://mcp.example.com
```

Lenses HQ (reached via `LENSES_ADVERTISED_URL`) must support:
- **OAuth 2.0 Authorization Server Metadata** ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414)) at `/.well-known/oauth-authorization-server`
- **Token Introspection** ([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)) at the `introspection_endpoint`, with client authentication **disabled**
- **PKCE with S256** ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) for client authorization flows

The MCP server does not send client credentials when introspecting a token.
On the Lenses HQ side this requires:

```yaml
oauth2:
  authorizationServer:
    unauthenticatedIntrospection: true
```

in the Lenses HQ config. Without this flag the introspection endpoint will
reject the MCP server's unauthenticated POST and every bearer token will be
rejected as invalid.

### Running with OAuth

```bash
# Local development
LENSES_URL=https://lenses.example.com \
MCP_ADVERTISED_URL=http://localhost:8000 \
uv run src/lenses_mcp/server.py
```

```bash
# Docker
docker run -p 8000:8000 \
   -e LENSES_URL=https://lenses.example.com \
   -e MCP_ADVERTISED_URL=http://localhost:8000 \
   lensesio/mcp
```

When `MCP_ADVERTISED_URL` is not set, the server falls back to the static `LENSES_API_KEY` for backward compatibility and `TRANSPORT` defaults to `stdio`.
