import json
import unittest
from typing import Any, Dict, Iterable, Optional

from sprintiq_sdk import GraphRAGClient, SprintIQClient


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

    def request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None, json: Any = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> DummyResponse:
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


class SprintIQGraphRAGClientTests(unittest.TestCase):
    def test_search_graphrag_applies_microsoft_delegation(self) -> None:
        client, session = make_client({"answer": "done"})
        result = client.search_graphrag(
            "Where is the workspace?",
            use_microsoft_cli=True,
            microsoft_cli={"workspacePath": "/tmp/workspace"},
            org_id="org-123",
            team_id="team-9",
            environment="staging",
            max_tokens=256,
            disable_evaluation=True,
        )

        self.assertEqual(result["answer"], "done")
        request = session.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "https://example.test/graphrag/search")
        payload = request["json"]
        self.assertEqual(payload["org_id"], "org-123")
        self.assertEqual(payload["team_id"], "team-9")
        self.assertEqual(payload["environment"], "staging")
        self.assertTrue(payload["disable_evaluation"])
        overrides = payload["config_overrides"]
        self.assertEqual(overrides["engine"], "microsoft")
        self.assertEqual(overrides["microsoft"]["workspacePath"], "/tmp/workspace")

    def test_search_graphrag_merges_config_overrides_without_mutation(self) -> None:
        client, session = make_client({"ok": True})
        overrides = {"query": {"maxTokens": 5000}}

        client.search_graphrag("hello", engine="native", config_overrides=overrides)

        payload = session.requests[0]["json"]["config_overrides"]
        self.assertEqual(payload["engine"], "native")
        self.assertEqual(payload["query"]["maxTokens"], 5000)
        # original reference unchanged
        self.assertEqual(overrides["query"]["maxTokens"], 5000)

    def test_graph_rag_client_injects_context(self) -> None:
        client, session = make_client({"answer": "context"})
        rag = GraphRAGClient(client, org_id="org-777", environment="prod", team_id="team-xyz")

        rag.search("hello world", use_microsoft_cli=False)

        request = session.requests[0]
        payload = request["json"]
        self.assertEqual(payload["org_id"], "org-777")
        self.assertEqual(payload["team_id"], "team-xyz")
        overrides = payload.get("config_overrides", {})
        self.assertEqual(overrides.get("engine"), "native")

    def test_index_graphrag_requires_documents_or_ids(self) -> None:
        client, _ = make_client()
        with self.assertRaises(ValueError):
            client.index_graphrag([])

    def test_incremental_index_supports_document_ids(self) -> None:
        client, session = make_client({"status": "queued"})

        client.incremental_index_graphrag([], document_ids=["doc-1"], org_id="org-001")

        payload = session.requests[0]["json"]
        self.assertEqual(payload["document_ids"], ["doc-1"])
        self.assertEqual(payload["mode"], "incremental")
        self.assertEqual(payload["org_id"], "org-001")


if __name__ == "__main__":
    unittest.main()
