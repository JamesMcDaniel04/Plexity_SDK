from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from plexity_sdk import (
    AsyncPlexityClient,
    ExecutionSummary,
    PlexityClient,
    WorkflowSummary,
)


class DummyResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400
        self.is_success = self.ok
        self.headers: Dict[str, str] = {"content-type": "application/json"}
        self.text = "" if payload is None else str(payload)

    def json(self) -> Any:
        return self._payload


class RecordingSession:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[Dict[str, Any]] = []

    def request(self, method: str, url: str, params=None, json=None, headers=None, timeout=None) -> DummyResponse:
        self.calls.append({"method": method, "url": url, "params": params, "json": json})
        return DummyResponse(self.payload)

    def close(self) -> None:
        pass


class MockAsyncClient:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[Dict[str, Any]] = []
        self.closed = False

    async def request(self, method: str, url: str, params=None, json=None, headers=None, timeout=None) -> DummyResponse:
        self.calls.append({"method": method, "url": url, "params": params, "json": json})
        return DummyResponse(self.payload)

    async def aclose(self) -> None:
        self.closed = True


def test_list_workflows_typed_sync() -> None:
    session = RecordingSession([{"id": "wf-1", "name": "Test"}])
    client = PlexityClient(base_url="https://example.test", session=session)

    workflows = client.list_workflows_typed()

    assert workflows == [WorkflowSummary(id="wf-1", name="Test", description=None)]


def test_get_execution_typed_sync() -> None:
    payload = {"id": "exec-1", "workflow_id": "wf", "status": "running"}
    session = RecordingSession(payload)
    client = PlexityClient(base_url="https://example.test", session=session)

    execution = client.get_execution_typed("exec-1")

    assert execution == ExecutionSummary(id="exec-1", workflow_id="wf", status="running", created_at=None, updated_at=None, metadata=None)


@pytest.mark.asyncio
async def test_list_workflows_typed_async() -> None:
    async_client = MockAsyncClient([{"id": "wf-2", "description": "Async"}])
    client = AsyncPlexityClient(base_url="https://example.test", client=async_client)

    workflows = await client.list_workflows_typed()

    assert workflows[0].id == "wf-2"
    assert not workflows[0].name
    await client.aclose()
    assert client._closed  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_execution_typed_async() -> None:
    payload = {"id": "exec-2", "status": "completed", "updated_at": "2024-01-01T00:00:00Z"}
    async_client = MockAsyncClient(payload)
    client = AsyncPlexityClient(base_url="https://example.test", client=async_client)

    execution = await client.get_execution_typed("exec-2")

    assert execution.id == "exec-2"
    assert execution.status == "completed"
    await client.aclose()
