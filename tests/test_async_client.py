from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from plexity_sdk import AsyncPlexityClient


class DummyResponse:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.status_code = 200
        self.ok = True
        self._payload = payload or {}
        self.headers: Dict[str, str] = {"content-type": "application/json"}
        self.text = ""

    def json(self) -> Dict[str, Any]:
        return self._payload


class RecordingSession:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.payload = payload or {}
        self.calls: list[Dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, params=None, json=None, headers=None, timeout=None) -> DummyResponse:
        self.calls.append({"method": method, "url": url, "json": json, "params": params})
        return DummyResponse(self.payload)

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_async_client_proxies_sync_methods() -> None:
    async_client = AsyncPlexityClient(base_url="https://example.test")
    session = RecordingSession({"items": []})
    sync_client = async_client.unwrap()
    sync_client._session = session  # type: ignore[attr-defined]
    sync_client._owns_session = True  # type: ignore[attr-defined]

    async with async_client as client:
        workflows = await client.list_workflows()
        assert workflows == {"items": []}
        assert session.calls[0]["url"] == "https://example.test/workflows"

    assert session.closed


@pytest.mark.asyncio
async def test_async_client_exposes_underlying_client() -> None:
    session = RecordingSession({})
    async_client = AsyncPlexityClient(base_url="https://example.test", session=session, max_retries=1)
    try:
        sync_client = async_client.unwrap()
        assert sync_client.base_url == "https://example.test"
        result = await async_client.run_in_executor(lambda: 7 * 6)
        assert result == 42
    finally:
        await async_client.close()
