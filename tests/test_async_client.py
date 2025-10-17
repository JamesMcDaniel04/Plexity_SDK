from __future__ import annotations

import httpx
import pytest

from plexity_sdk import AsyncPlexityClient


class DummyResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.is_success = status_code < 400
        self.headers = {"content-type": "application/json"}
        self.text = ""

    def json(self):
        return self._payload


class MockAsyncClient:
    def __init__(self, payload, failures: int = 0):
        self.payload = payload
        self.failures = failures
        self.calls = 0
        self.closed = False

    async def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        if self.calls < self.failures:
            self.calls += 1
            raise httpx.HTTPError("boom")
        self.calls += 1
        return DummyResponse(self.payload)

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_async_client_requests_are_awaitable():
    http_client = MockAsyncClient({"items": []})
    client = AsyncPlexityClient(base_url="https://example.test", client=http_client)

    data = await client.list_workflows()

    assert data == {"items": []}
    assert http_client.calls == 1
    await client.aclose()
    assert http_client.closed


@pytest.mark.asyncio
async def test_async_client_retries_transport_errors(monkeypatch):
    http_client = MockAsyncClient({"answer": 42}, failures=2)
    client = AsyncPlexityClient(base_url="https://example.test", client=http_client, max_retries=2, retry_backoff_factor=0)

    result = await client.list_workflows()

    assert result == {"answer": 42}
    assert http_client.calls == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_async_client_aclose_is_idempotent():
    http_client = MockAsyncClient({})
    client = AsyncPlexityClient(base_url="https://example.test", client=http_client)

    await client.aclose()
    await client.aclose()  # second close should be a no-op
    assert http_client.closed
