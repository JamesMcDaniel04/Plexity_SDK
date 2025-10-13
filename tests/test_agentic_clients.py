import json
import unittest
from typing import Any, Dict, Optional

from plexity_sdk import (
    ContextClient,
    MCPClient,
    PlexityClient,
    TeamDelegationClient,
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


def make_client(payload: Optional[Dict[str, Any]] = None) -> tuple[PlexityClient, RecordingSession]:
    session = RecordingSession(payload=payload)
    client = PlexityClient(base_url="https://example.test", session=session)
    return client, session


class ContextClientTests(unittest.TestCase):
    def test_list_context_entries_serialises_filters(self) -> None:
        client, session = make_client({"items": []})
        context = ContextClient(client)

        context.list(page=2, limit=50, tag="integration", priority="HIGH", search="ok", include_inactive=True)

        req = session.requests[0]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://example.test/context")
        params = req["params"]
        assert params is not None
        self.assertEqual(params["page"], "2")
        self.assertEqual(params["limit"], "50")
        self.assertEqual(params["tag"], "integration")
        self.assertEqual(params["priority"], "HIGH")
        self.assertEqual(params["search"], "ok")
        self.assertEqual(params["include_inactive"], "true")

    def test_create_context_entry_requires_title_and_content(self) -> None:
        client, _ = make_client()
        context = ContextClient(client)
        with self.assertRaises(ValueError):
            context.create(title="", content="data")
        with self.assertRaises(ValueError):
            context.create(title="Valid", content="")

    def test_update_context_entry_builds_payload(self) -> None:
        client, session = make_client({"contextEntry": {"id": "ctx-1"}})
        context = ContextClient(client)

        context.update("ctx-1", title="Updated", priority="CRITICAL", is_active=False)

        req = session.requests[0]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(req["url"], "https://example.test/context/ctx-1")
        payload = req["json"]
        self.assertEqual(payload["title"], "Updated")
        self.assertEqual(payload["priority"], "CRITICAL")
        self.assertFalse(payload["isActive"])


class MCPClientTests(unittest.TestCase):
    def test_create_mcp_server_payload(self) -> None:
        client, session = make_client({"id": "srv-1"})
        mcp = MCPClient(client)

        mcp.create_server(name="Context7", base_url="https://context7.test", api_key="secret", enabled=False)

        req = session.requests[0]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://example.test/mcp/servers")
        payload = req["json"]
        self.assertEqual(payload["name"], "Context7")
        self.assertEqual(payload["base_url"], "https://context7.test")
        self.assertEqual(payload["api_key"], "secret")
        self.assertFalse(payload["enabled"])

    def test_update_mcp_server_requires_fields(self) -> None:
        client, _ = make_client()
        mcp = MCPClient(client)
        with self.assertRaises(ValueError):
            mcp.update_server("srv-1")


class TeamDelegationClientTests(unittest.TestCase):
    def test_list_tasks_uses_default_team(self) -> None:
        client, session = make_client({"tasks": []})
        delegation = TeamDelegationClient(client, team_id="team-default")

        delegation.list_tasks(status=["active", "pending"], limit=25)

        req = session.requests[0]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://example.test/team-delegation/tasks")
        params = req["params"]
        assert params is not None
        self.assertEqual(params["team_id"], "team-default")
        self.assertEqual(params["status"], "active,pending")
        self.assertEqual(params["limit"], "25")

    def test_create_task_merges_defaults(self) -> None:
        client, session = make_client({"task": {"id": "task-1"}})
        delegation = TeamDelegationClient(client, team_id="team-42")

        delegation.create_task(title="Ship feature", tags=["priority-high"], assignee_ids=["user-1"])

        req = session.requests[0]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://example.test/team-delegation/tasks")
        payload = req["json"]
        self.assertEqual(payload["team_id"], "team-42")
        self.assertEqual(payload["title"], "Ship feature")
        self.assertEqual(payload["tags"], ["priority-high"])
        self.assertEqual(payload["assignee_ids"], ["user-1"])

    def test_bulk_status_requires_ids(self) -> None:
        client, _ = make_client()
        delegation = TeamDelegationClient(client)
        with self.assertRaises(ValueError):
            delegation.bulk_update_status(task_ids=[], status="closed")


if __name__ == "__main__":
    unittest.main()

