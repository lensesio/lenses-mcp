"""RFC 7662 Token Introspection with auto-discovery.

On the first ``verify_token`` call the verifier:

1. Fetches ``{auth_server_url}/.well-known/oauth-authorization-server``
   to discover the ``introspection_endpoint`` (unless an explicit URL was
   provided at construction time).
2. Calls the introspection endpoint **without** client authentication —
   the endpoint is unauthenticated.

Subsequent calls skip discovery and go straight to the introspection
endpoint.

Token resolution (``resolve_token``) still forwards the raw bearer token
to the Lenses API so that Lenses can perform its own authorization checks.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass

import httpx
from config import LENSES_API_KEY
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from loguru import logger

logger = logger.bind(name="auth")


@dataclass
class _CacheEntry:
    """Cached introspection result with expiration."""

    result: AccessToken
    expires_at: float


class DiscoveryTokenVerifier(TokenVerifier):
    """Token verifier that discovers its introspection endpoint from auth server metadata.

    The introspection endpoint is called without client credentials — the
    endpoint does not require authentication.

    Initialization is deferred to the first ``verify_token`` call so the
    server can start without blocking on network I/O.
    """

    _MAX_CACHE_SIZE = 10_000

    def __init__(
        self,
        auth_server_url: str,
        introspection_url: str | None = None,
        required_scopes: list[str] | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes)
        self._auth_server_url = auth_server_url.rstrip("/")
        self._introspection_url_override = introspection_url
        self._cache_ttl = cache_ttl_seconds or 0
        self._introspection_url: str | None = introspection_url
        self._discovered = introspection_url is not None
        self._init_lock = asyncio.Lock()
        self._cache: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Metadata discovery
    # ------------------------------------------------------------------

    async def _discover(self) -> None:
        """Fetch auth server metadata to resolve the introspection endpoint."""
        metadata_url = f"{self._auth_server_url}/.well-known/oauth-authorization-server"
        logger.info("Discovering auth server metadata from {}", metadata_url)

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(metadata_url)
            resp.raise_for_status()
            metadata = resp.json()

        self._introspection_url = metadata.get(
            "introspection_endpoint",
            f"{self._auth_server_url}/oauth2/introspect",
        )
        self._discovered = True
        logger.info("Introspection endpoint: {}", self._introspection_url)

    # ------------------------------------------------------------------
    # Caching helpers
    #
    # Caching avoids a network round-trip to the introspection endpoint on
    # every MCP tool call. The trade-off is delayed revocation detection:
    # a token revoked at the auth server won't be rejected until its cache
    # entry expires. Caching is therefore disabled by default (TTL = 0);
    # set INTROSPECTION_CACHE_TTL to a positive value to opt in.
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_cached(self, token: str) -> AccessToken | None:
        if self._cache_ttl <= 0:
            return None
        key = self._hash_token(token)
        entry = self._cache.get(key)
        if entry is None or entry.expires_at < time.time():
            if entry is not None:
                del self._cache[key]
            return None
        return entry.result

    def _set_cached(self, token: str, result: AccessToken) -> None:
        if self._cache_ttl <= 0:
            return
        if len(self._cache) >= self._MAX_CACHE_SIZE:
            del self._cache[next(iter(self._cache))]
        key = self._hash_token(token)
        expires_at = time.time() + self._cache_ttl
        if result.expires_at:
            expires_at = min(expires_at, float(result.expires_at))
        self._cache[key] = _CacheEntry(result=result, expires_at=expires_at)

    # ------------------------------------------------------------------
    # Scope extraction (RFC 7662)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_scopes(data: dict) -> list[str]:
        scope = data.get("scope")
        if isinstance(scope, str):
            return [s.strip() for s in scope.split() if s.strip()]
        if isinstance(scope, list):
            return [str(s) for s in scope if s]
        return []

    # ------------------------------------------------------------------
    # Token verification
    # ------------------------------------------------------------------

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify *token* via RFC 7662, bootstrapping discovery on first call."""

        # Lazy discovery
        if not self._discovered:
            async with self._init_lock:
                if not self._discovered:
                    try:
                        await self._discover()
                    except Exception:
                        logger.opt(exception=True).error("Auth server discovery failed — rejecting token")
                        return None
        if self._introspection_url is None:
            return None

        # Cache check
        cached = self._get_cached(token)
        if cached is not None:
            return cached

        # RFC 7662 introspection — unauthenticated POST
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._introspection_url,
                    data={"token": token, "token_type_hint": "access_token"},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )

            if resp.status_code != 200:
                logger.debug("Introspection returned HTTP {}", resp.status_code)
                return None

            data = resp.json()

            if not data.get("active", False):
                logger.debug("Token introspection returned active=false")
                return None

            client_id = data.get("client_id") or data.get("sub", "unknown")

            exp = data.get("exp")
            if exp and exp < time.time():
                logger.debug("Introspected token is expired")
                return None

            scopes = self._extract_scopes(data)

            if self.required_scopes and not set(self.required_scopes).issubset(set(scopes)):
                logger.debug(
                    "Token missing required scopes. Has: {}, Required: {}",
                    scopes,
                    self.required_scopes,
                )
                return None

            result = AccessToken(
                token=token,
                client_id=str(client_id),
                scopes=scopes,
                expires_at=int(exp) if exp else None,
                claims=data,
            )
            self._set_cached(token, result)
            return result

        except httpx.TimeoutException:
            logger.debug("Introspection request timed out")
            return None
        except httpx.RequestError as e:
            logger.debug("Introspection request failed: {}", e)
            return None
        except Exception as e:
            logger.debug("Introspection error: {}", e)
            return None


def resolve_token() -> str:
    """Bearer token to forward to Lenses for the current call.

    Resolution order:
    1. Per-request token from FastMCP's auth context (OAuth / introspection).
    2. Static ``LENSES_API_KEY`` from env (legacy / stdio fallback).
    3. ToolError if neither is available.
    """
    try:
        access_token = get_access_token()
    except (LookupError, RuntimeError):
        access_token = None  # outside a request context (e.g. stdio)

    if access_token is not None:
        return access_token.token

    if LENSES_API_KEY:
        return LENSES_API_KEY

    raise ToolError("Authentication required")
