"""Tests for configuration parsing and defaults."""

import importlib
import os
import sys
from unittest.mock import patch

import pytest

# Minimum env for API-key mode (OAUTH_ENABLED defaults to false)
_API_KEY_ENV = {"LENSES_API_KEY": "test-key"}


def _reload_config(**env: str):
    """Reload ``config`` with the given env vars patched in and return it.

    ``config`` captures values at import time, so we need a fresh import for
    each test case to observe the effect of different env var combinations.

    ``load_dotenv`` is stubbed out so the real ``.env`` file on disk does not
    leak into the test environment.
    """
    with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
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
    config = _reload_config(**_API_KEY_ENV)

    assert config.LENSES_API_HTTP_URL == "http://localhost"
    assert config.LENSES_API_HTTP_PORT == "9991"
    assert config.LENSES_API_WEBSOCKET_URL == "ws://localhost"
    assert config.LENSES_API_WEBSOCKET_PORT == "9991"


def test_https_url_derives_wss():
    """Config derives wss:// websocket URL from https:// LENSES_URL."""
    config = _reload_config(LENSES_URL="https://lenses.example.com:443", **_API_KEY_ENV)

    assert config.LENSES_API_HTTP_URL == "https://lenses.example.com"
    assert config.LENSES_API_HTTP_PORT == "443"
    assert config.LENSES_API_WEBSOCKET_URL == "wss://lenses.example.com"
    assert config.LENSES_API_WEBSOCKET_PORT == "443"


# ---------------------------------------------------------------------------
# OAUTH_ENABLED parsing
# ---------------------------------------------------------------------------


def test_oauth_enabled_defaults_to_false():
    """OAUTH_ENABLED is False when unset."""
    config = _reload_config(**_API_KEY_ENV)
    assert config.OAUTH_ENABLED is False


@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "YES"])
def test_oauth_enabled_truthy_values(value):
    """Common truthy strings are accepted."""
    config = _reload_config(
        OAUTH_ENABLED=value,
        MCP_ADVERTISED_URL="http://localhost:8000",
        LENSES_URL="https://lenses.example.com",
    )
    assert config.OAUTH_ENABLED is True


@pytest.mark.parametrize("value", ["false", "False", "0", "no", ""])
def test_oauth_enabled_falsy_values(value):
    """Non-truthy strings resolve to False."""
    config = _reload_config(OAUTH_ENABLED=value, **_API_KEY_ENV)
    assert config.OAUTH_ENABLED is False


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------


def test_validation_oauth_missing_mcp_advertised_url():
    """OAUTH_ENABLED=true without MCP_ADVERTISED_URL raises EnvironmentError."""
    with pytest.raises(EnvironmentError, match="MCP_ADVERTISED_URL"):
        _reload_config(
            OAUTH_ENABLED="true",
            LENSES_ADVERTISED_URL="https://lenses.example.com",
        )


def test_validation_api_key_mode_missing_key():
    """OAUTH_ENABLED=false without LENSES_API_KEY raises EnvironmentError."""
    with pytest.raises(EnvironmentError, match="LENSES_API_KEY"):
        _reload_config(OAUTH_ENABLED="false")


def test_validation_api_key_mode_empty_key():
    """An empty LENSES_API_KEY is treated as missing."""
    with pytest.raises(EnvironmentError, match="LENSES_API_KEY"):
        _reload_config(OAUTH_ENABLED="false", LENSES_API_KEY="")


# ---------------------------------------------------------------------------
# OAuth gate & transport default — OAUTH_ENABLED drives both
# ---------------------------------------------------------------------------


def test_transport_defaults_to_stdio_without_oauth():
    """OAUTH_ENABLED=false → TRANSPORT defaults to stdio (local dev)."""
    config = _reload_config(**_API_KEY_ENV)
    assert config.TRANSPORT == "stdio"
    assert config.OAUTH_ENABLED is False


def test_transport_defaults_to_http_with_oauth():
    """OAUTH_ENABLED=true → TRANSPORT defaults to http automatically."""
    config = _reload_config(
        OAUTH_ENABLED="true",
        MCP_ADVERTISED_URL="http://localhost:8000",
        LENSES_URL="https://lenses.example.com",
    )
    assert config.TRANSPORT == "http"
    assert config.OAUTH_ENABLED is True


def test_explicit_transport_overrides_oauth_default():
    """An explicit TRANSPORT env var wins over the OAuth-based default."""
    config = _reload_config(
        OAUTH_ENABLED="true",
        MCP_ADVERTISED_URL="http://localhost:8000",
        LENSES_URL="https://lenses.example.com",
        TRANSPORT="sse",
    )
    assert config.TRANSPORT == "sse"


def test_explicit_stdio_transport_without_oauth():
    """TRANSPORT=stdio explicitly set → still stdio, no surprises."""
    config = _reload_config(TRANSPORT="stdio", **_API_KEY_ENV)
    assert config.TRANSPORT == "stdio"


def test_lenses_advertised_url_defaults_to_lenses_url():
    """When unset, LENSES_ADVERTISED_URL falls back to LENSES_URL.

    This simplifies the simple-deployment case: operators only set LENSES_URL.
    """
    config = _reload_config(LENSES_URL="https://lenses.example.com", **_API_KEY_ENV)
    assert config.LENSES_ADVERTISED_URL == "https://lenses.example.com"
    assert config.LENSES_URL == "https://lenses.example.com"


def test_lenses_advertised_url_explicit_override():
    """In split-plane deployments, an explicit LENSES_ADVERTISED_URL wins."""
    config = _reload_config(
        LENSES_URL="http://lenses.internal:9991",
        LENSES_ADVERTISED_URL="https://hq.example.com",
        **_API_KEY_ENV,
    )
    assert config.LENSES_URL == "http://lenses.internal:9991"
    assert config.LENSES_ADVERTISED_URL == "https://hq.example.com"


# ---------------------------------------------------------------------------
# oauth_required_scopes helper
# ---------------------------------------------------------------------------


def test_oauth_required_scopes_returns_dependency_when_oauth_on():
    """With OAUTH_ENABLED=true, oauth_required_scopes returns a real dependency."""
    config = _reload_config(
        OAUTH_ENABLED="true",
        MCP_ADVERTISED_URL="http://localhost:8000",
        LENSES_URL="https://lenses.example.com",
    )
    result = config.oauth_required_scopes("read")
    assert result is not None


def test_oauth_required_scopes_returns_none_when_oauth_off():
    """With OAUTH_ENABLED=false, oauth_required_scopes returns None."""
    config = _reload_config(**_API_KEY_ENV)
    result = config.oauth_required_scopes("read")
    assert result is None
