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
    UV_SYSTEM_PYTHON=1 \
    UV_NO_SYNC=1 \
    FASTMCP_LOG_LEVEL=INFO \
    FASTMCP_STATELESS_HTTP=true

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies, generate third-party license report,
# then clean up the temporary pip-licenses tool.
# Note: uv sync creates .venv even with UV_SYSTEM_PYTHON=1, so we must
# install pip-licenses into the venv (--python) for it to see prod deps.
RUN uv sync --frozen --no-dev \
    && uv pip install --python .venv/bin/python pip-licenses \
    && uv run pip-licenses \
         --ignore-packages pip-licenses prettytable wcwidth \
         --format=plain-vertical \
         --with-license-file \
         --no-license-path \
         --output-file=NOTICE.txt \
    && uv sync --frozen --no-dev

# Copy application source code and license file
COPY LICENSE ./
COPY src/ ./src/

# Copy environment example (users should use their own /app/.env or set env vars)
COPY .env.example ./.env.example

# Set default transport to stdio
ENV TRANSPORT=stdio

# Expose port for HTTP transport
ENV PORT=8000
EXPOSE 8000

USER lensesmcp

# Default command runs the MCP server via its own __main__ entrypoint, so the
# CORS middleware and auth wiring in server.py are applied. Transport, host,
# port, and stateless_http are all read from env vars by config.py.
CMD ["uv", "run", "python", "src/lenses_mcp/server.py"]
