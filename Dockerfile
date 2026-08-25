# ── Builder ────────────────────────────────────
# Resolves the dependency tree and generates the third-party license
# report. Nothing from this stage ships except the virtualenv and
# NOTICE.txt, so uv and its toolchain never reach the runtime image.
FROM python:3.13-alpine AS builder

# uv is pinned deliberately: an unpinned tag makes builds irreproducible
# and silently freezes whatever version was current at build time.
# The -alpine variant is musl-linked, as required by this base image.
COPY --from=ghcr.io/astral-sh/uv:0.12.5-alpine /usr/local/bin/uv /usr/local/bin/uv

# Use the interpreter already in the base image rather than letting uv
# fetch a managed CPython, so the venv we copy out matches the runtime.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

WORKDIR /lenses-mcp

COPY pyproject.toml uv.lock ./

# Install production dependencies, generate the third-party license
# report from that same environment, then re-sync to drop pip-licenses
# and its transitive deps back out of the venv.
RUN uv sync --frozen --no-dev \
    && uv pip install --python .venv/bin/python pip-licenses \
    && .venv/bin/pip-licenses \
         --ignore-packages pip-licenses prettytable wcwidth \
         --format=plain-vertical \
         --with-license-file \
         --no-license-path \
         --output-file=NOTICE.txt \
    && uv sync --frozen --no-dev

# ── Runtime ────────────────────────────────────
FROM python:3.13-alpine

LABEL org.opencontainers.image.authors="Lenses.io Engineering <info@lenses.io>"
LABEL org.opencontainers.image.ref.name="lensesio/mcp"
LABEL org.opencontainers.image.vendor="Lenses.io"

# The server never installs packages at runtime, so pip and setuptools
# are pure attack surface (and a recurring source of CVE findings).
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip* \
              /usr/local/lib/python3.13/site-packages/setuptools* \
              /usr/local/lib/python3.13/site-packages/wheel* \
              /usr/local/lib/python3.13/site-packages/pkg_resources \
    && addgroup -g 60000 lensesmcp \
    && adduser -D -h /lenses-mcp -u 60000 -G lensesmcp lensesmcp \
    && chmod 755 /lenses-mcp

WORKDIR /lenses-mcp

# Putting the venv first on PATH is what lets the entrypoint be a plain
# `python` call instead of `uv run`.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTMCP_LOG_LEVEL=INFO \
    FASTMCP_STATELESS_HTTP=true \
    PATH="/lenses-mcp/.venv/bin:$PATH" \
    TRANSPORT=stdio \
    PORT=8000

COPY --from=builder /lenses-mcp/.venv ./.venv
COPY --from=builder /lenses-mcp/NOTICE.txt ./NOTICE.txt

# Copy application source code and license file
COPY LICENSE ./
COPY src/ ./src/

# Copy environment example (users should use their own /app/.env or set env vars)
COPY .env.example ./.env.example

# Expose port for HTTP transport
EXPOSE 8000

USER lensesmcp

# server.py is run as a script: Python puts src/lenses_mcp/ at the head of
# sys.path, which is how its flat `from config import ...` imports resolve.
# Transport, host, port, and stateless_http are all read from env by config.py.
CMD ["python", "src/lenses_mcp/server.py"]
