"""Async HTTP client for the Ficsit Remote Monitoring mod.

Thin wrapper over ``httpx.AsyncClient`` that fetches FRM endpoints with a timeout
and a short-TTL per-path cache (the mod is polled frequently; caching avoids
hammering it). Returns raw JSON — normalization lives in
:mod:`app.connectors.frm.normalize`, keeping raw shapes inside this package.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.errors import UpstreamUnavailableError

logger = logging.getLogger(__name__)


class FrmClient:
    """Fetches and caches raw FRM endpoint payloads.

    Args:
        base_url: FRM mod base URL (e.g. ``http://localhost:8080``).
        timeout: Per-request timeout in seconds.
        cache_ttl: Seconds to reuse a cached response for a given path.
        transport: Optional httpx transport override (used by tests).
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        cache_ttl: float = 2.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._cache_ttl = cache_ttl
        self._client = httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout, transport=transport
        )
        self._cache: dict[str, tuple[float, Any]] = {}

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get(self, path: str, *, use_cache: bool = True) -> Any:
        """GET a path and return parsed JSON, raising on failure.

        Raises:
            UpstreamUnavailableError: on connection/timeout/HTTP errors.
        """
        key = path.lstrip("/")
        now = time.monotonic()
        if use_cache:
            cached = self._cache.get(key)
            if cached is not None and now - cached[0] < self._cache_ttl:
                return cached[1]
        try:
            response = await self._client.get(f"/{key}")
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamUnavailableError(
                f"FRM request to {path!r} failed: {exc}", details={"path": path}
            ) from exc
        self._cache[key] = (now, data)
        return data

    async def healthy(self) -> bool:
        """Return True if the FRM mod answers a lightweight probe."""
        try:
            await self.get("getPower", use_cache=False)
            return True
        except UpstreamUnavailableError:
            return False
