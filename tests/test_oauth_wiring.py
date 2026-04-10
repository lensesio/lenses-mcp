"""Tests for the OAuth wiring in server.build_auth_provider() — split-plane invariants.

These tests pin down the contract that:
- Token introspection MUST go to the internal Lenses address
  (``internal_lenses_base``), not to ``lenses_advertised_url`` — the
  advertised URL is for clients only.
- The advertised URL is what gets published in protected-resource metadata.
- Discovery is bypassed entirely so the verifier never accidentally extracts
  a public URL from Lenses HQ's metadata response.

Regression coverage for the issue Cursor Bugbot caught in PR #7: introspection
was wired to ``LENSES_ADVERTISED_URL``, breaking split-plane deployments where
the MCP server cannot reach the public URL.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "lenses_mcp"))

from server import build_auth_provider

# ---------------------------------------------------------------------------
# Split-plane invariants — the regression we're locking down
# ---------------------------------------------------------------------------


def test_split_plane_introspection_uses_internal_url():
    """In a split-plane deployment, introspection MUST use the internal Lenses URL.

    Cursor Bugbot caught this in PR #7 review: previously the verifier was
    given LENSES_ADVERTISED_URL as auth_server_url, which meant it tried to
    POST to the public URL — unreachable from inside the cluster. The fix
    routes introspection through the same internal address the data-plane
    HTTP client uses.
    """
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read", "write", "delete"],
    )
    verifier = auth.token_verifier
    assert verifier._auth_server_url == "http://lenses.internal:9991"
    assert verifier._introspection_url == "http://lenses.internal:9991/oauth2/introspect"


def test_split_plane_advertises_public_url_to_clients():
    """The advertised URL stays public — clients need to reach it from their browsers."""
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read", "write", "delete"],
    )
    advertised = [str(u) for u in auth.authorization_servers]
    assert advertised == ["https://lenses.example.com/"]
    assert str(auth.base_url) == "https://mcp.example.com/"


def test_discovery_is_bypassed_entirely():
    """The verifier must skip discovery — Lenses HQ would return public URLs.

    Even if we point discovery at the internal URL, Lenses HQ's metadata
    response advertises issuer/introspection_endpoint as the *public* URL,
    which the MCP server cannot reach. The only safe pattern is to never
    call _discover() at all, by passing introspection_url at construction.
    """
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read", "write", "delete"],
    )
    assert auth.token_verifier._discovered is True, (
        "discovery must be pre-skipped (introspection_url set at construction)"
    )


# ---------------------------------------------------------------------------
# Simple deployment — single URL for everything
# ---------------------------------------------------------------------------


def test_simple_deployment_uses_lenses_url_for_both():
    """In a single-URL deployment, internal and advertised URLs are the same value."""
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        # In a simple deployment, server.py wires both of these from LENSES_URL
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="https://lenses.example.com:443",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read", "write", "delete"],
    )
    verifier = auth.token_verifier
    assert verifier._auth_server_url == "https://lenses.example.com:443"
    assert verifier._introspection_url == "https://lenses.example.com:443/oauth2/introspect"
    advertised = [str(u) for u in auth.authorization_servers]
    assert advertised == ["https://lenses.example.com/"]


# ---------------------------------------------------------------------------
# Explicit INTROSPECTION_URL override — escape hatch
# ---------------------------------------------------------------------------


def test_explicit_introspection_url_overrides_internal_default():
    """An explicit introspection_url overrides the internal-URL default.

    Escape hatch for deployments where the introspection endpoint is on a
    completely separate host from the data-plane API.
    """
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url="https://custom-idp.example/introspect",
        introspection_cache_ttl=0,
        mcp_scopes=["read", "write", "delete"],
    )
    assert auth.token_verifier._introspection_url == "https://custom-idp.example/introspect"


# ---------------------------------------------------------------------------
# Cache TTL passthrough
# ---------------------------------------------------------------------------


def test_introspection_cache_ttl_zero_means_no_cache():
    """A TTL of 0 disables caching (passes None to the verifier)."""
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read"],
    )
    assert auth.token_verifier._cache_ttl == 0


def test_introspection_cache_ttl_positive_enables_cache():
    """A positive TTL enables introspection result caching."""
    auth = build_auth_provider(
        mcp_advertised_url="https://mcp.example.com",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=300,
        mcp_scopes=["read"],
    )
    assert auth.token_verifier._cache_ttl == 300


# ---------------------------------------------------------------------------
# OAuth disabled — no auth provider, no protected-resource endpoint
# ---------------------------------------------------------------------------


def test_no_oauth_when_mcp_advertised_url_is_none():
    """Without mcp_advertised_url, build_auth_provider returns None."""
    auth = build_auth_provider(
        mcp_advertised_url=None,
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read"],
    )
    assert auth is None


def test_no_oauth_when_mcp_advertised_url_is_empty_string():
    """An empty string is also falsy — no OAuth."""
    auth = build_auth_provider(
        mcp_advertised_url="",
        lenses_advertised_url="https://lenses.example.com",
        internal_lenses_base="http://lenses.internal:9991",
        introspection_url=None,
        introspection_cache_ttl=0,
        mcp_scopes=["read"],
    )
    assert auth is None
