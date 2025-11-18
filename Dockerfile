FROM python:3.12-slim

LABEL org.opencontainers.image.authors="Lenses.io Engineering <info@lenses.io>"
LABEL org.opencontainers.image.ref.name="lensesio/mcp"
LABEL org.opencontainers.image.vendor="Lenses.io"

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create user to run the application
RUN useradd -d /lenses-mcp -m -U -u 60000 lensesmcp \
    && chmod 755 /lenses-mcp

WORKDIR /lenses-mcp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src/ ./src/

# Copy environment example (users should use their own /app/.env or set env vars)
COPY .env.example ./.env.example

# Set default transport to stdio
ENV TRANSPORT=stdio

# Expose port for HTTP transport
ENV PORT=8000
EXPOSE 8000

USER lensesmcp

# Default command runs the MCP server with configurable transport
# For stdio: only --transport is used
# For http/sse: --transport, --port, and --host are used
CMD ["/bin/sh", "-c", "\
    if [ \"${TRANSPORT}\" = \"stdio\" ]; then \
        uv run fastmcp run src/lenses_mcp/server.py --transport=${TRANSPORT}; \
    else \
        uv run fastmcp run src/lenses_mcp/server.py --transport=${TRANSPORT} --port=${PORT} --host=0.0.0.0; \
    fi"]
