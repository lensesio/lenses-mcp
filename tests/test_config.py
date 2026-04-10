"""Tests for configuration parsing and defaults."""

import importlib
import os
import sys
from unittest.mock import patch


def _reload_config(**env: str):
    """Reload ``config`` with the given env vars patched in and return it.

    ``config`` captures values at import time, so we need a fresh import for
    each test case to observe the effect of different env var combinations.
    """
    with patch.dict(os.environ, env, clear=True):
        for mod_name in list(sys.modules):
            if mod_name == "config" or mod_name.startswith("config."):
                del sys.modules[mod_name]
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))
        try:
            import config

            importlib.reload(config)
            return config
        finally:
            sys.path.pop(0)


def test_default_lenses_url():
    """Config defaults to http://localhost:9991 when LENSES_URL is not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Re-import to pick up the patched environment
        import importlib
        import sys

        # Remove cached module so it re-evaluates env vars
        for mod_name in list(sys.modules):
            if mod_name == "config" or mod_name.startswith("config."):
                del sys.modules[mod_name]

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))
        try:
            import config

            importlib.reload(config)

            assert config.LENSES_API_HTTP_URL == "http://localhost"
            assert config.LENSES_API_HTTP_PORT == "9991"
            assert config.LENSES_API_WEBSOCKET_URL == "ws://localhost"
            assert config.LENSES_API_WEBSOCKET_PORT == "9991"
        finally:
            sys.path.pop(0)


def test_https_url_derives_wss():
    """Config derives wss:// websocket URL from https:// LENSES_URL."""
    with patch.dict(os.environ, {"LENSES_URL": "https://lenses.example.com:443"}, clear=True):
        for mod_name in list(sys.modules):
            if mod_name == "config" or mod_name.startswith("config."):
                del sys.modules[mod_name]

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))
        try:
            import config

            importlib.reload(config)

            assert config.LENSES_API_HTTP_URL == "https://lenses.example.com"
            assert config.LENSES_API_HTTP_PORT == "443"
            assert config.LENSES_API_WEBSOCKET_URL == "wss://lenses.example.com"
            assert config.LENSES_API_WEBSOCKET_PORT == "443"
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# OAuth gate & transport default — MCP_ADVERTISED_URL drives both
# ---------------------------------------------------------------------------


def test_transport_defaults_to_stdio_without_oauth():
    """No MCP_ADVERTISED_URL → TRANSPORT defaults to stdio (local dev)."""
    config = _reload_config()
    assert config.TRANSPORT == "stdio"
    assert config.MCP_ADVERTISED_URL is None


def test_transport_defaults_to_http_with_oauth():
    """MCP_ADVERTISED_URL set → TRANSPORT defaults to http automatically."""
    config = _reload_config(MCP_ADVERTISED_URL="http://localhost:8000")
    assert config.TRANSPORT == "http"
    assert config.MCP_ADVERTISED_URL == "http://localhost:8000"


def test_explicit_transport_overrides_oauth_default():
    """An explicit TRANSPORT env var wins over the OAuth-based default."""
    config = _reload_config(MCP_ADVERTISED_URL="http://localhost:8000", TRANSPORT="sse")
    assert config.TRANSPORT == "sse"


def test_explicit_stdio_transport_without_oauth():
    """TRANSPORT=stdio explicitly set → still stdio, no surprises."""
    config = _reload_config(TRANSPORT="stdio")
    assert config.TRANSPORT == "stdio"


def test_lenses_advertised_url_defaults_to_lenses_url():
    """When unset, LENSES_ADVERTISED_URL falls back to LENSES_URL.

    This simplifies the simple-deployment case: operators only set LENSES_URL.
    """
    config = _reload_config(LENSES_URL="https://lenses.example.com")
    assert config.LENSES_ADVERTISED_URL == "https://lenses.example.com"
    assert config.LENSES_URL == "https://lenses.example.com"


def test_lenses_advertised_url_explicit_override():
    """In split-plane deployments, an explicit LENSES_ADVERTISED_URL wins."""
    config = _reload_config(
        LENSES_URL="http://lenses.internal:9991",
        LENSES_ADVERTISED_URL="https://hq.example.com",
    )
    assert config.LENSES_URL == "http://lenses.internal:9991"
    assert config.LENSES_ADVERTISED_URL == "https://hq.example.com"
