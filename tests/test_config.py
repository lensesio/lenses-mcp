"""Tests for configuration parsing and defaults."""

import os
from unittest.mock import patch


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
        import importlib
        import sys

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
