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
from typing import TYPE_CHECKING

import httpx
from config import LENSES_API_KEY
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger

logger = logger.bind(name="auth")


class AuthenticationRequiredError(ToolError):
    """Raised when Lenses has rejected a token that introspection had accepted.

    Signals to the caller that their existing session is no longer valid and
    a fresh OAuth flow is required. Callers that raise this also evict the
    token from the introspection cache via ``invalidate_cached_token`` so the
    next request triggers fresh introspection and — if the token is still
    bad — a standard upstream 401+``WWW-Authenticate`` challenge.
    """


def token_fingerprint(token: str) -> str:
    """Short, stable, non-reversible identifier for a token, suitable for logs.

    Multi-user OAuth deployments need a way to correlate log lines for the
    same user without ever logging the raw bearer token. Returns the first
    eight hex characters of the token's SHA-256 hash — roughly 32 bits of
    entropy, enough to distinguish concurrent sessions by eye while being
    cheap, stable across calls, and impossible to reverse.

    The prefix is a substring of the key used by ``DiscoveryTokenVerifier``
    for cache keying, so an operator with access to both the logs and a
    cache dump can match entries by string prefix.
    """
    return hashlib.sha256(token.encode()).hexdigest()[:8]


def handle_downstream_401(
    token: str,
    *,
    detail: str,
    context: str,
    client_logger: Logger,
) -> AuthenticationRequiredError:
    """Build the re-auth signal for a 401 received from a downstream Lenses call.

    Evicts any cached introspection result for ``token`` and returns an
    ``AuthenticationRequiredError`` the caller should ``raise ... from e``.
    Invalidation failures are logged but never propagated — a broken cache
    layer must not shadow the user-facing re-auth signal.

    ``context`` is a short human-readable phrase ("with 401", "on WebSocket
    handshake with 401") included in the warning log for correlation.
    ``client_logger`` is the caller's bound loguru logger so warnings keep
    the caller's name (HTTPClient / WebSocketClient) for log routing.
    """
    token_fp = token_fingerprint(token)
    try:
        invalidate_cached_token(token)
    except Exception:
        client_logger.opt(exception=True).warning("Failed to invalidate cached token (fp={}) {}", token_fp, context)
    client_logger.warning("Lenses rejected token (fp={}) {}: {}", token_fp, context, detail)
    return AuthenticationRequiredError(
        f"Authentication error: {detail}. Please re-authenticate — your session has expired or been revoked."
    )


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

    def invalidate(self, token: str) -> None:
        """Remove ``token`` from the introspection cache if present.

        Called when a downstream consumer (e.g. the Lenses HTTP client) has
        observed that the token is no longer accepted, so the cached positive
        result is stale and must not be reused.
        """
        if self._cache_ttl <= 0:
            return
        self._cache.pop(self._hash_token(token), None)

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
        fp = token_fingerprint(token)
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
                logger.warning(
                    "Introspection rejected token (fp={}): HTTP {} — {}",
                    fp,
                    resp.status_code,
                    resp.text[:500],
                )
                return None

            data = resp.json()

            if not data.get("active", False):
                logger.warning("Introspection rejected token (fp={}): active=false", fp)
                return None

            client_id = data.get("client_id") or data.get("sub", "unknown")

            exp = data.get("exp")
            if exp and exp < time.time():
                logger.warning("Introspection rejected token (fp={}): expired (exp={})", fp, exp)
                return None

            scopes = self._extract_scopes(data)

            if self.required_scopes and not set(self.required_scopes).issubset(set(scopes)):
                logger.warning(
                    "Introspection rejected token (fp={}): missing required scopes. Has: {}, Required: {}",
                    fp,
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
            logger.warning("Introspection request timed out for token (fp={})", fp)
            return None
        except httpx.RequestError as e:
            logger.warning("Introspection request failed for token (fp={}): {}", fp, e)
            return None
        except Exception as e:
            logger.warning("Introspection error for token (fp={}): {}", fp, e)
            return None


def invalidate_cached_token(token: str) -> None:
    """Evict ``token`` from the active server's introspection cache, if any.

    Looks up the running FastMCP server via ``get_server()`` and calls
    ``invalidate`` on its ``DiscoveryTokenVerifier`` if one is attached.

    Safe no-op when:
    - Called outside a request context (e.g. stdio startup)
    - The server has no auth provider (unauthenticated deployments)
    - The attached verifier isn't a ``DiscoveryTokenVerifier`` (e.g. tests with
      a different verifier, future migration to a different auth scheme)
    - Caching is disabled (``INTROSPECTION_CACHE_TTL=0``)
    """
    from fastmcp.server.dependencies import get_server

    try:
        server = get_server()
    except RuntimeError:
        return  # no active request context
    verifier = getattr(server.auth, "token_verifier", None)
    if isinstance(verifier, DiscoveryTokenVerifier):
        verifier.invalidate(token)


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
