from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from functools import partial
from typing import Any, Awaitable, Callable, Optional, TypeVar

from .client import PlexityClient

__all__ = ["AsyncPlexityClient"]

T = TypeVar("T")


class AsyncPlexityClient:
    """Asynchronous facade for :class:`plexity_sdk.client.PlexityClient`.

    Methods on the underlying synchronous client are executed in a background
    thread using :func:`asyncio.to_thread` or a custom executor. This keeps the
    API surface identical for callers that prefer `await` semantics.
    """

    def __init__(
        self,
        *,
        executor: Optional[Executor] = None,
        client_factory: Callable[..., PlexityClient] = PlexityClient,
        **client_kwargs: Any,
    ) -> None:
        self._client = client_factory(**client_kwargs)
        self._executor = executor
        self._closed = False

    async def close(self) -> None:
        if self._closed:
            return
        await self.run_in_executor(self._client.close)
        self._closed = True

    async def __aenter__(self) -> "AsyncPlexityClient":
        if self._closed:
            raise RuntimeError("cannot reuse a closed AsyncPlexityClient")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def run_in_executor(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a callable in the configured executor and await its result."""
        if self._executor is None:
            return await asyncio.to_thread(func, *args, **kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, partial(func, *args, **kwargs))

    def unwrap(self) -> PlexityClient:
        """Expose the underlying synchronous client for advanced scenarios."""
        return self._client

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if callable(attr):

            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.run_in_executor(attr, *args, **kwargs)

            async_wrapper.__name__ = getattr(attr, "__name__", name)
            async_wrapper.__doc__ = getattr(attr, "__doc__", None)
            return async_wrapper
        return attr
