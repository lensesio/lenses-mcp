# 🌊🔍 Lenses MCP Server for Apache Kafka 🔎🌊

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org/)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.4.7-green)](https://gofastmcp.com/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green)](https://modelcontextprotocol.io/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

This is the [Lenses](https://lenses.io/) MCP (Model Context Protocol) server for Apache Kafka. Lenses offers a developer experience solution for engineers building real-time applications connected to Kafka. It's built for the enterprise and backed by a powerful IAM and governance model. 

With Lenses, you can find, explore, transform, integrate and replicate data across a multi-Kafka and vendor estate. Now, all this power is accessible through your AI tools and AI Agents via MCP, bringing real-time context into your agentic engineering workflows.

The quickest way to try the MCP server is with the free [Lenses Community Edition](https://lenses.io/community-edition/), which runs Lenses MCP Server as a remote MCP server and comes with a pre-configured single broker Kafka cluster with demo data, ideal for local development or evaluation ([steps here](https://docs.lenses.io/latest/mcp/lenses-mcp-server/getting-started/run-with-community-edition)).

## Table of Contents

- [1. Install uv and Python](#1-install-uv-and-python)
- [2. Configure Environment Variables](#2-configure-environment-variables)
- [3. OAuth 2.1 Authentication (Recommended)](#3-oauth-21-authentication-recommended)
- [4. Lenses API Key (Fallback)](#4-lenses-api-key-fallback)
- [5. Running the Server Locally](#5-running-the-server-locally)
- [6. Running with Docker](#6-running-with-docker)
- [7. OpenTelemetry Tracing](#7-opentelemetry-tracing)
- [8. Optional Context7 MCP Server](#8-optional-context7-mcp-server)
- [Appendix: OAuth Flow Details](#appendix-oauth-flow-details)


## 1. Install uv and Python

We use `uv` for dependency management and project setup. If you don't have `uv` installed, follow the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).

This project requires *Python 3.13* (any 3.13.x release). To verify your Python version, run:

```bash
uv run python --version
```

## 2. Configure Environment Variables

Copy the example environment file and configure it based on your authentication method:

```bash
cp .env.example .env
```

**Required variables** depend on your authentication choice:

- **For OAuth** (recommended): `LENSES_URL` and `MCP_ADVERTISED_URL`
- **For API Key** (fallback): `LENSES_URL` and `LENSES_API_KEY`


## 3. OAuth 2.1 Authentication (Recommended)

OAuth 2.1 is the recommended authentication method for all Lenses MCP deployments. It provides secure, scope-based authorization without sharing static API keys.

### How it works

OAuth 2.1 uses bearer tokens that are validated via [RFC 7662 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662). The flow involves three participants:

1. **MCP Client** — Your AI tool (Claude, Cursor, etc.)
2. **Authorization Server** — Lenses HQ at `LENSES_ADVERTISED_URL`
3. **MCP Server** — This server (the resource server)

When you connect, the client automatically:
1. Discovers OAuth metadata from this server (`/.well-known/oauth-protected-resource/mcp`)
2. Registers itself with the authorization server
3. Initiates OAuth authorization (with PKCE) and gets an access token
4. Uses the token to authenticate requests to this MCP server

This server then validates the token with Lenses HQ before allowing access to Kafka resources.

### Simple setup

To use OAuth, you should set `OAUTH_ENABLED` to `true`, then you only need to set two environment variables:

```bash
OAUTH_ENABLED=true
LENSES_URL=https://lenses.example.com
MCP_ADVERTISED_URL=http://localhost:8000
```

- `LENSES_URL` — Your Lenses instance (used internally and as the OAuth authorization server)
- `MCP_ADVERTISED_URL` — The public URL where this MCP server is reachable by clients

`TRANSPORT` automatically defaults to `http` when `MCP_ADVERTISED_URL` is set.

### Advanced: split-plane deployments

If the MCP server reaches Lenses on an internal address but clients reach it on a public URL:

```bash
OAUTH_ENABLED=true
LENSES_URL=http://lenses-hq.internal:9991
LENSES_ADVERTISED_URL=https://lenses.example.com
MCP_ADVERTISED_URL=https://mcp.example.com
```

### Authorization scopes

The server advertises three scopes:

| Scope | Description |
|-------|-------------|
| `read` | Read-only access to Lenses resources (topics, environments, connectors, etc.) |
| `write` | Create and update resources |
| `delete` | Delete resources |

When you authenticate, you'll be prompted to grant these scopes. Your token will only grant the scopes you select.

### Lenses HQ configuration

Lenses HQ must support OAuth 2.0 and token introspection. Ensure your Lenses HQ config includes:

```yaml
oauth2:
  authorizationServer:
    unauthenticatedIntrospection: true
```

This allows the MCP server to validate tokens without client credentials.

## 4. Lenses API Key (Fallback)

For backward compatibility and testing, you can use a static API key instead of OAuth. This is not recommended for production but may be useful for local development or legacy systems.

Create a Lenses API key by provisioning an [IAM Service Account](https://docs.lenses.io/latest/user-guide/iam/service-accounts) in Lenses. Add the API key to `.env`:

```bash
LENSES_URL=https://lenses.example.com
LENSES_API_KEY=<YOUR_LENSES_API_KEY>
```

When using API key authentication, `TRANSPORT` defaults to `stdio` (local only) unless you explicitly set `MCP_ADVERTISED_URL`.

## 5. Running the Server Locally

First, install dependencies:

```bash
uv sync
```

### With OAuth (Recommended)

Run with stdio transport (for local AI tools):

```bash
OAUTH_ENABLED=true \
LENSES_URL=https://lenses.example.com \
MCP_ADVERTISED_URL=http://localhost:8000 \
uv run src/lenses_mcp/server.py
```

Or run with HTTP transport (for remote clients):

```bash
OAUTH_ENABLED=true \
LENSES_URL=https://lenses.example.com \
MCP_ADVERTISED_URL=http://localhost:8000 \
uv run fastmcp run src/lenses_mcp/server.py --transport=http --port=8000
```

To configure in Claude Desktop, Cursor, or similar tools:

```json
{
  "mcpServers": {
    "Lenses": {
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
        "OAUTH_ENABLED": "true",
        "LENSES_URL": "https://lenses.example.com",
        "MCP_ADVERTISED_URL": "http://localhost:8000"
      },
      "transport": "stdio"
    }
  }
}
```

### With API Key (Legacy)

Using a static API key:

```bash
LENSES_URL=https://lenses.example.com \
LENSES_API_KEY=<YOUR_LENSES_API_KEY> \
uv run src/lenses_mcp/server.py
```

Or with HTTP transport:

```bash
LENSES_URL=https://lenses.example.com \
LENSES_API_KEY=<YOUR_LENSES_API_KEY> \
uv run fastmcp run src/lenses_mcp/server.py --transport=http --port=8000
```

To configure in Claude Desktop, Cursor, or similar tools:

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
        "LENSES_URL": "https://lenses.example.com",
        "LENSES_API_KEY": "<YOUR_LENSES_API_KEY>"
      },
      "transport": "stdio"
    }
  }
}
```

Note: Some clients may require the absolute path to `uv` in the command.

## 6. Running with Docker

The Lenses MCP server is available as a Docker image at `lensesio/mcp`. You can run it with OAuth (recommended) or API key authentication.

### With OAuth (Recommended)

**Stdio transport** (for local AI tools):

```bash
docker run --rm -it \
  -e OAUTH_ENABLED=true \
  -e LENSES_URL=https://lenses.example.com \
  -e MCP_ADVERTISED_URL=http://localhost:8000 \
  lensesio/mcp
```

**HTTP transport** (for remote clients, listens on `http://0.0.0.0:8000/mcp`):

```bash
docker run --rm -it -p 8000:8000 \
  -e OAUTH_ENABLED=true \
  -e LENSES_URL=https://lenses.example.com \
  -e MCP_ADVERTISED_URL=http://localhost:8000 \
  -e TRANSPORT=http \
  lensesio/mcp
```

For split-plane deployments where the MCP server reaches Lenses internally but clients use a public URL:

```bash
docker run --rm -it -p 8000:8000 \
  -e OAUTH_ENABLED=true \
  -e LENSES_URL=http://lenses-hq.internal:9991 \
  -e LENSES_ADVERTISED_URL=https://lenses.example.com \
  -e MCP_ADVERTISED_URL=https://mcp.example.com \
  -e TRANSPORT=http \
  lensesio/mcp
```

### With API Key (Legacy)

**Stdio transport** (for local AI tools):

```bash
docker run --rm -it \
  -e LENSES_API_KEY=<YOUR_API_KEY> \
  -e LENSES_URL=https://lenses.example.com \
  lensesio/mcp
```

**HTTP transport** (for remote clients, listens on `http://0.0.0.0:8000/mcp`):

```bash
docker run --rm -it -p 8000:8000 \
  -e LENSES_API_KEY=<YOUR_API_KEY> \
  -e LENSES_URL=https://lenses.example.com \
  -e TRANSPORT=http \
  lensesio/mcp
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OAUTH_ENABLED` | No | `false` | Enables/disables OAuth |
| `LENSES_URL` | Yes | `http://localhost:9991` | Lenses instance URL in format `[scheme]://[host]:[port]`. Use `https://` for secure connections (automatically uses `wss://` for WebSockets) |
| `MCP_ADVERTISED_URL` | For OAuth | - | Public base URL of this MCP server as reachable by clients. Setting this enables OAuth and defaults `TRANSPORT` to `http` |
| `LENSES_API_KEY` | For API Key auth | - | Your Lenses API key (create via [IAM Service Account](https://docs.lenses.io/latest/user-guide/iam/service-accounts)). Only needed if not using OAuth |
| `TRANSPORT` | No | `http` if `MCP_ADVERTISED_URL` is set, else `stdio` | Transport mode: `stdio`, `http` |
| `PORT` | No | `8000` | Port to listen on (only used with `http` transport) |
| `LENSES_ADVERTISED_URL` | No | `LENSES_URL` | Public Lenses HQ URL advertised to MCP clients for OAuth. Override only in split-plane deployments |
| `MCP_SCOPES` | No | `read,write,delete` | Comma-separated OAuth scopes advertised in protected-resource metadata |
| `INTROSPECTION_URL` | No | Discovered from `LENSES_ADVERTISED_URL` metadata | Override for the RFC 7662 token introspection endpoint URL |
| `INTROSPECTION_CACHE_TTL` | No | `0` (disabled) | Cache TTL for introspection results in seconds |
| `OTEL_ENABLED` | No | `false` | Export OpenTelemetry traces (see [section 7](#7-opentelemetry-tracing)) |
| `OTEL_EXPORTER` | No | `otlp` | `otlp` to send to a collector, or `console` to print spans for debugging |
| `OTEL_SERVICE_NAME` | No | `lenses-mcp` | Service name reported to the tracing backend |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://localhost:4318` | Collector base URL. Read by the OpenTelemetry SDK, so all standard `OTEL_*` variables apply |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | No | `http/protobuf` | `http/protobuf` (port 4318) or `grpc` (port 4317, needs the `otlp-grpc` extra) |

**Legacy environment variables** (for backward compatibility):
- `LENSES_API_HTTP_URL`, `LENSES_API_HTTP_PORT`
- `LENSES_API_WEBSOCKET_URL`, `LENSES_API_WEBSOCKET_PORT`

These are automatically derived from `LENSES_URL` but can be explicitly set to override.

### Transport Endpoints

- **stdio**: Standard input/output (no network endpoint)
- **http**: HTTP endpoint at `/mcp`
- **sse**: Server-Sent Events endpoint at `/sse`

### Building the Docker Image Locally

To build the Docker image locally:

```bash
docker build -t lensesio/mcp .
```

## 7. OpenTelemetry Tracing

The server is built on FastMCP 4, which emits an OpenTelemetry span for every
MCP request — `tools/call <tool_name>`, `tools/list`, `prompts/get <prompt_name>`
and so on. Spans carry the tool or prompt name, the MCP session id, the
negotiated protocol version, and error status when a call fails.

Tracing is **off by default** and costs nothing until you switch it on.

### Enabling

```bash
OTEL_ENABLED=true \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
uv run python src/lenses_mcp/server.py
```

With Docker:

```bash
docker run -p 8000:8000 \
   -e LENSES_URL=<your-lenses-url> \
   -e LENSES_API_KEY=<your-api-key> \
   -e TRANSPORT=http \
   -e OTEL_ENABLED=true \
   -e OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318 \
   lensesio/mcp
```

`OTEL_EXPORTER_OTLP_ENDPOINT` is a **base** URL — the SDK appends `/v1/traces`
for HTTP. Point it at the collector root, not at the traces path. Use
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` if you need to specify the full URL.

### Exporters

The OTLP **HTTP** exporter (port 4318) is included by default. The gRPC
exporter (port 4317) pulls in `grpcio` and adds roughly 27MB to the image, so
it is an optional extra:

```bash
uv sync --extra otlp-grpc
# then
OTEL_EXPORTER_OTLP_PROTOCOL=grpc OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317 ...
```

Asking for `grpc` without the extra installed logs a warning and leaves tracing
off; it never prevents the server from starting. The same is true of any other
telemetry misconfiguration — an unreachable collector or a bad exporter name is
logged and the server carries on serving requests.

### Verifying locally

The quickest check needs no collector — print spans to stderr:

```bash
OTEL_ENABLED=true OTEL_EXPORTER=console uv run python src/lenses_mcp/server.py
```

The console exporter writes to **stderr**, not stdout: with the default `stdio`
transport, stdout carries the JSON-RPC wire and anything else printed there
would corrupt it. Redirect stderr to a file if the spans crowd your terminal:

```bash
OTEL_ENABLED=true OTEL_EXPORTER=console \
uv run python src/lenses_mcp/server.py 2>spans.log
```

For a trace UI, Jaeger accepts OTLP/HTTP on 4318 and serves its UI on 16686:

```bash
docker run -p 16686:16686 -p 4318:4318 \
  -e COLLECTOR_OTLP_ENABLED=true jaegertracing/all-in-one:1.62.0
```

Then browse <http://localhost:16686> and select the `lenses-mcp` service.

### Trace context propagation

Spans are emitted per MCP request; there is no session-level parent span. A
nested trace only forms when the **client** propagates trace context
(`traceparent` in the request `_meta`), which FastMCP extracts and parents
from. Clients that are not OpenTelemetry-instrumented produce one root trace
per call, which is expected. To get grouped traces, instrument the agent that
calls this server.

## 8. Optional Context7 MCP Server

Lenses documentation is available on [Context7](https://context7.com/websites/lenses_io). It is optional but highly recommended to use the [Context7 MCP Server](https://github.com/upstash/context7) and adjust your prompts with `use context7` to ensure the documentation available to the LLM is up to date.

## Appendix: OAuth Flow Details

### Token validation sequence

The MCP server validates bearer tokens using the following sequence:

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

### Configuration and Requirements

In a simple deployment, only two environment variables are required:

```bash
LENSES_URL=https://lenses.example.com
MCP_ADVERTISED_URL=http://localhost:8000
```

For **split-plane deployments** where the MCP server reaches Lenses on an internal address but clients use a public URL, set:

```bash
LENSES_URL=http://lenses-hq.internal:9991
LENSES_ADVERTISED_URL=https://lenses.example.com
MCP_ADVERTISED_URL=https://mcp.example.com
```

Lenses HQ must support:

- **OAuth 2.0 Authorization Server Metadata** ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414)) at `/.well-known/oauth-authorization-server`
- **Token Introspection** ([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)) at the `introspection_endpoint`, with client authentication **disabled**
- **PKCE with S256** ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) for client authorization flows

The MCP server does not send client credentials when introspecting. Lenses HQ must be configured with:

```yaml
oauth2:
  authorizationServer:
    unauthenticatedIntrospection: true
```

Without this setting, every bearer token will be rejected as invalid.
