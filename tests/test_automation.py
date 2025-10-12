import json
import unittest
from typing import Any, Dict, Optional

from sprintiq_sdk import (
    ClaudeAutomationClient,
    IntegrationAutomationClient,
    IntegrationPlan,
    SprintIQClient,
)


class DummyResponse:
    def __init__(self, payload: Optional[Dict[str, Any]] = None, status_code: int = 200) -> None:
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload or {}
        self.headers: Dict[str, str] = {"content-type": "application/json"}
        self.text = json.dumps(self._payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


class RecordingSession:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self._payload = payload or {}
        self.requests: list[Dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> DummyResponse:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return DummyResponse(self._payload)


def make_client(payload: Optional[Dict[str, Any]] = None) -> tuple[SprintIQClient, RecordingSession]:
    session = RecordingSession(payload=payload)
    client = SprintIQClient(base_url="https://example.test", session=session)
    return client, session


class SprintIQIntegrationApiTests(unittest.TestCase):
    def test_clone_repository_sends_auth_header(self) -> None:
        client, session = make_client({"ok": True})
        client.clone_repository(repository_url="https://github.com/org/repo", auth_token="token-123", shallow_clone=False)

        req = session.requests[0]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://example.test/github/clone")
        self.assertEqual(req["json"]["repository_url"], "https://github.com/org/repo")
        self.assertFalse(req["json"]["shallow_clone"])
        self.assertEqual(req["headers"]["authorization"], "Bearer token-123")

    def test_create_pull_request_payload(self) -> None:
        client, session = make_client({"pr": "ok"})
        client.create_github_pull_request(
            repository_url="https://github.com/org/repo",
            repository_path="/tmp/repo",
            branch_name="feature-x",
            base_branch="main",
            title="Automated",
            body="Details",
        )

        req = session.requests[0]
        self.assertEqual(req["url"], "https://example.test/github/create-pr")
        payload = req["json"]
        self.assertEqual(payload["branch_name"], "feature-x")
        self.assertEqual(payload["base_branch"], "main")
        self.assertEqual(payload["title"], "Automated")
        self.assertEqual(payload["description"], "Details")

    def test_create_claude_session_default_payload(self) -> None:
        client, session = make_client({"session": "id"})
        client.create_claude_session(repository_name="Repo", tasks=[{"name": "Task"}])

        req = session.requests[0]
        self.assertEqual(req["url"], "https://example.test/claude-agent/sessions")
        payload = req["json"]
        self.assertEqual(payload["repository_name"], "Repo")
        self.assertEqual(payload["tasks"][0]["name"], "Task")


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Dict[str, Any]]] = []

    def clone_repository(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("clone", kwargs))
        return {"local_path": "/tmp/repo"}

    def prepare_integration(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("prepare", kwargs))
        return {"local_path": "/tmp/repo"}

    def install_integration_dependencies(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("install", kwargs))
        return {"installed": True}

    def write_integration_files(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("write", kwargs))
        return {"written": True}

    def run_integration_tests(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("test", kwargs))
        return {"status": "passed"}

    def create_github_pull_request(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("pr", kwargs))
        return {"pull_request": {"number": 42}}


class IntegrationAutomationClientTests(unittest.TestCase):
    def test_apply_plan_runs_full_pipeline(self) -> None:
        fake_client = FakeClient()
        automation = IntegrationAutomationClient(fake_client, auth_token="secret")
        plan = IntegrationPlan(
            files={"config.yml": "value: 1"},
            dependencies=["dep1"],
            dev_dependencies=["dev-dep"],
            python_dependencies=["requests"],
            metadata={"summary": "Automated integration plan"},
        )

        result = automation.apply_plan(
            repository_url="https://github.com/org/repo",
            plan=plan,
            branch_name="feature/graph",
            base_branch="develop",
            pull_request_title="Integration PR",
        )

        call_names = [name for name, _ in fake_client.calls]
        self.assertEqual(
            call_names,
            ["clone", "prepare", "install", "write", "test", "pr"],
        )
        self.assertIn("pull_request", result)


class FakeClaudeClient:
    def __init__(self) -> None:
        self.payload: Optional[Dict[str, Any]] = None

    def create_claude_session(self, **kwargs: Any) -> Dict[str, Any]:
        self.payload = kwargs
        return {"session_id": "session-1"}


class ClaudeAutomationClientTests(unittest.TestCase):
    def test_delegate_repository_setup_uses_default_tasks(self) -> None:
        client = ClaudeAutomationClient(FakeClaudeClient())
        response = client.delegate_repository_setup(repository_name="Repo")
        self.assertEqual(response["session_id"], "session-1")
        assert isinstance(client._client, FakeClaudeClient)
        assert client._client.payload is not None
        self.assertEqual(len(client._client.payload["tasks"]), 3)


if __name__ == "__main__":
    unittest.main()

