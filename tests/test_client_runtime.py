from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
import requests

from plexity_sdk import PlexityClient, PlexityError


class DummyResponse:
    def __init__(self, payload: Optional[Dict[str, Any]] = None, status_code: int = 200) -> None:
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload or {}
        self.headers: Dict[str, str] = {"content-type": "application/json"}
        self.text = ""

    def json(self) -> Dict[str, Any]:
        return self._payload


class ClosingSession:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self._payload = payload or {}
        self.closed = False
        self.calls = 0

    def request(self, method: str, url: str, params=None, json=None, headers=None, timeout=None) -> DummyResponse:
        self.calls += 1
        return DummyResponse(self._payload)

    def close(self) -> None:
        self.closed = True


def test_context_manager_closes_owned_session() -> None:
    session = ClosingSession({"items": []})
    client = PlexityClient(base_url="https://example.test")
    client._session = session  # type: ignore[attr-defined]
    client._owns_session = True  # type: ignore[attr-defined]
    with client:
        data = client.list_workflows()
        assert isinstance(data, dict)
    assert session.closed


class FlakySession:
    def __init__(self, failures: int, payload: Dict[str, Any]) -> None:
        self.failures = failures
        self.payload = payload
        self.calls = 0

    def request(self, method: str, url: str, params=None, json=None, headers=None, timeout=None) -> DummyResponse:
        if self.calls < self.failures:
            self.calls += 1
            raise requests.ConnectionError("boom")
        self.calls += 1
        return DummyResponse(self.payload)

    def close(self) -> None:
        pass


def test_retries_on_transport_errors() -> None:
    session = FlakySession(failures=2, payload={"answer": 42})
    client = PlexityClient(base_url="https://example.test", session=session, max_retries=2, retry_backoff_factor=0)

    result = client.list_workflows()

    assert result == {"answer": 42}
    assert session.calls == 3


def test_raises_transport_error_after_exhausting_retries() -> None:
    session = FlakySession(failures=5, payload={})
    client = PlexityClient(base_url="https://example.test", session=session, max_retries=2, retry_backoff_factor=0)

    with pytest.raises(PlexityError) as exc:
        client.list_workflows()

    assert exc.value.status_code == 0
    assert "transport_error" in str(exc.value)
