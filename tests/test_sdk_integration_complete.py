"""
Comprehensive integration test to verify all missing agentic layers are present in the SDK.

This test validates that the SDK now exposes the five previously missing layers:
1. Memory & MCP context management
2. Task delegation & synchronization
3. Insight generation pipeline
4. Integration orchestration & data sync
5. Team operations (via automation clients)
"""

import unittest
from typing import Any, Dict, Optional

from plexity_sdk import (
    PlexityClient,
    ContextClient,
    MCPClient,
    TeamDelegationClient,
    IntegrationAutomationClient,
    ClaudeAutomationClient,
    IntegrationPlan,
    InsightClient,
)


class DummyResponse:
    """Mock HTTP response for testing."""

    def __init__(self, payload: Optional[Dict[str, Any]] = None, status_code: int = 200) -> None:
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload or {}
        self.headers: Dict[str, str] = {"content-type": "application/json"}
        self.text = str(self._payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


class RecordingSession:
    """Mock requests session that records calls."""

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
    """Create a test client with recording session."""
    session = RecordingSession(payload=payload)
    client = PlexityClient(base_url="https://api.test.local", session=session)
    return client, session


class Layer1ContextMemoryTests(unittest.TestCase):
    """Test Layer 1: Memory & MCP context management."""

    def test_context_client_exists(self):
        """Verify ContextClient is exposed in SDK."""
        client, _ = make_client()
        context = ContextClient(client)
        self.assertIsNotNone(context)

    def test_mcp_client_exists(self):
        """Verify MCPClient is exposed in SDK."""
        client, _ = make_client()
        mcp = MCPClient(client)
        self.assertIsNotNone(mcp)

    def test_context_crud_operations(self):
        """Verify context CRUD operations are wired to correct endpoints."""
        client, session = make_client({"id": "ctx-1", "title": "Test Context"})
        context = ContextClient(client)

        # Create
        context.create(title="Test", content="Test content", tags=["test"])
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/context")

        # List
        context.list(page=1, limit=10, tag="test")
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/context")

        # Get
        context.get("ctx-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/context/ctx-1")

        # Update
        context.update("ctx-1", title="Updated", priority="HIGH")
        req = session.requests[-1]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(req["url"], "https://api.test.local/context/ctx-1")

        # Delete
        context.delete("ctx-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "DELETE")
        self.assertEqual(req["url"], "https://api.test.local/context/ctx-1")

    def test_mcp_server_operations(self):
        """Verify MCP server management operations."""
        client, session = make_client({"id": "srv-1"})
        mcp = MCPClient(client)

        # List servers
        mcp.list_servers()
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/mcp/servers")

        # Create server
        mcp.create_server(name="Context7", base_url="https://context7.io", enabled=True)
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/mcp/servers")

        # Update server
        mcp.update_server("srv-1", enabled=False)
        req = session.requests[-1]
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(req["url"], "https://api.test.local/mcp/servers/srv-1")

        # Health check
        mcp.check_health("srv-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/mcp/servers/srv-1/health")

        # Delete server
        mcp.delete_server("srv-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "DELETE")
        self.assertEqual(req["url"], "https://api.test.local/mcp/servers/srv-1")


class Layer2TaskDelegationTests(unittest.TestCase):
    """Test Layer 2: Task delegation & synchronization."""

    def test_team_delegation_client_exists(self):
        """Verify TeamDelegationClient is exposed."""
        client, _ = make_client()
        delegation = TeamDelegationClient(client, team_id="team-1")
        self.assertIsNotNone(delegation)

    def test_task_crud_operations(self):
        """Verify task CRUD operations."""
        client, session = make_client({"task": {"id": "task-1"}})
        delegation = TeamDelegationClient(client, team_id="team-test")

        # List tasks
        delegation.list_tasks(status=["active"], limit=10)
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks")

        # Create task
        delegation.create_task(
            title="Implement feature",
            description="Add GraphRAG support",
            priority="high",
            tags=["backend"],
        )
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks")
        self.assertEqual(req["json"]["team_id"], "team-test")

        # Get task
        delegation.get_task("task-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks/task-1")

        # Update task status
        delegation.update_task_status("task-1", status="completed")
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks/task-1/status")

    def test_bulk_operations(self):
        """Verify bulk task operations."""
        client, session = make_client({"updated": 5})
        delegation = TeamDelegationClient(client)

        # Bulk status update
        delegation.bulk_update_status(task_ids=["t1", "t2"], status="closed")
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks/bulk/status")

        # Bulk assign
        delegation.bulk_assign(task_ids=["t1", "t2"], assignee_ids=["u1"])
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks/bulk/assign")

    def test_task_export(self):
        """Verify task export functionality."""
        client, session = make_client({"tasks": []})
        delegation = TeamDelegationClient(client, team_id="team-1")

        delegation.export_tasks(status="active", format="json", include_updates=True)
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/team-delegation/tasks/export")


class Layer3InsightGenerationTests(unittest.TestCase):
    """Test Layer 3: Insight generation pipeline helpers."""

    def test_list_insight_jobs_serialises_filters(self):
        client, session = make_client({"jobs": [{"id": "job-1"}]})

        jobs = client.list_insight_jobs(
            status=["completed", "processing"],
            job_type="weekly_report",
            team_id="team-42",
            limit=25,
        )

        self.assertEqual(jobs, [{"id": "job-1"}])
        request = session.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs")
        params = request["params"]
        assert params is not None
        self.assertEqual(params["status"], "completed,processing")
        self.assertEqual(params["job_type"], "weekly_report")
        self.assertEqual(params["team_id"], "team-42")
        self.assertEqual(params["limit"], "25")

    def test_create_insight_job_payload(self):
        client, session = make_client({"job": {"id": "job-2"}})

        job = client.create_insight_job(
            job_type="weekly_report",
            payload={"week": "2024-10-07"},
            metadata={"initiator": "ops"},
            team_id="team-7",
            priority=3,
            delay_ms=60000,
        )

        self.assertEqual(job["id"], "job-2")
        request = session.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs")
        payload = request["json"]
        self.assertEqual(payload["job_type"], "weekly_report")
        self.assertEqual(payload["payload"], {"week": "2024-10-07"})
        self.assertEqual(payload["metadata"], {"initiator": "ops"})
        self.assertEqual(payload["team_id"], "team-7")
        self.assertEqual(payload["priority"], 3)
        self.assertEqual(payload["delay_ms"], 60000)

    def test_get_insight_job_and_result(self):
        client, session = make_client({"job": {"id": "job-3"}, "result": {"summary": "ok"}})

        job = client.get_insight_job("job-3")
        self.assertEqual(job["id"], "job-3")
        request = session.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs/job-3")

        result = client.get_insight_job_result("job-3")
        self.assertEqual(result, {"summary": "ok"})
        request = session.requests[1]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs/job-3/result")

    def test_get_latest_insight_job(self):
        client, session = make_client({"job": {"id": "job-latest"}})

        job = client.get_latest_insight_job(job_type="weekly_report")

        self.assertEqual(job["id"], "job-latest")
        request = session.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs/latest")
        params = request["params"]
        assert params is not None
        self.assertEqual(params["job_type"], "weekly_report")

    def test_insight_client_wrapper_delegates_to_base_client(self):
        client, session = make_client({"jobs": []})
        insight = InsightClient(client)

        insight.list_jobs(status=["queued"])

        request = session.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://api.test.local/insights/jobs")


class Layer4IntegrationOrchestrationTests(unittest.TestCase):
    """Test Layer 4: Integration orchestration & data sync."""

    def test_integration_automation_client_exists(self):
        """Verify IntegrationAutomationClient is exposed."""
        client, _ = make_client()
        automation = IntegrationAutomationClient(client)
        self.assertIsNotNone(automation)

    def test_repository_bootstrap(self):
        """Verify repository bootstrap workflow."""
        client, session = make_client(
            {"clone": {"local_path": "/tmp/repo"}, "prepare": {"local_path": "/tmp/repo"}}
        )
        automation = IntegrationAutomationClient(client)

        result = automation.bootstrap_repository(
            repository_url="https://github.com/test/repo",
            branch_name="feature-branch",
        )

        # Should make clone and prepare calls
        self.assertGreaterEqual(len(session.requests), 2)
        self.assertIn("repository_path", result)

    def test_dependency_installation(self):
        """Verify dependency installation."""
        client, session = make_client({"success": True})
        automation = IntegrationAutomationClient(client)

        automation.install_dependencies(
            repository_path="/tmp/repo",
            dependencies=["graphrag"],
            python_dependencies=["openai"],
        )

        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/integration/install-dependencies")

    def test_file_writing(self):
        """Verify file writing operations."""
        client, session = make_client({"written": 3})
        automation = IntegrationAutomationClient(client)

        automation.write_files(
            repository_path="/tmp/repo",
            files={"config.yaml": {"content": "test"}},
        )

        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/integration/write-files")

    def test_integration_plan_dataclass(self):
        """Verify IntegrationPlan dataclass."""
        plan = IntegrationPlan(
            files={"config.yaml": "content"},
            dependencies=["pkg1"],
            config={"key": "value"},
        )

        self.assertEqual(plan.files, {"config.yaml": "content"})
        # dependencies is stored as a tuple internally
        self.assertEqual(list(plan.dependencies), ["pkg1"])
        self.assertEqual(plan.config, {"key": "value"})

    def test_integration_plan_from_dict(self):
        """Verify IntegrationPlan.from_dict factory."""
        data = {
            "files": {"test.py": "code"},
            "dependencies": ["dep1", "dep2"],
            "metadata": {"author": "test"},
        }

        plan = IntegrationPlan.from_dict(data)
        self.assertEqual(plan.files, {"test.py": "code"})
        self.assertEqual(len(plan.dependencies), 2)
        self.assertEqual(plan.metadata, {"author": "test"})

    def test_pr_creation(self):
        """Verify pull request creation."""
        client, session = make_client({"pr": {"number": 123}})
        automation = IntegrationAutomationClient(client)

        automation.create_pull_request(
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/repo",
            branch_name="feature",
            title="Add GraphRAG",
        )

        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/github/create-pr")

    def test_apply_plan_workflow(self):
        """Verify full apply_plan workflow."""
        client, session = make_client(
            {
                "local_path": "/tmp/repo",
                "clone": {"local_path": "/tmp/repo"},
                "prepare": {"local_path": "/tmp/repo"},
                "success": True,
                "written": 1,
                "tests": {"passed": True},
                "pr": {"number": 456},
            }
        )
        automation = IntegrationAutomationClient(client)

        plan = IntegrationPlan(
            files={"config.yaml": "test"},
            dependencies=["graphrag"],
        )

        result = automation.apply_plan(
            repository_url="https://github.com/test/repo",
            plan=plan,
            run_tests=True,
            auto_pr=True,
        )

        # Should have bootstrap, dependencies, files, tests, and PR
        self.assertIn("bootstrap", result)
        self.assertIn("dependencies", result)
        self.assertIn("files", result)
        self.assertIn("tests", result)
        self.assertIn("pull_request", result)


class Layer5ClaudeAutomationTests(unittest.TestCase):
    """Test Layer 5: Claude agent automation (team operations)."""

    def test_claude_automation_client_exists(self):
        """Verify ClaudeAutomationClient is exposed."""
        client, _ = make_client()
        claude = ClaudeAutomationClient(client)
        self.assertIsNotNone(claude)

    def test_session_management(self):
        """Verify Claude session management."""
        client, session = make_client({"sessions": [], "session": {"id": "sess-1"}})
        claude = ClaudeAutomationClient(client)

        # List sessions
        claude.list_sessions(limit=10, status=["active"])
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/claude-agent/sessions")

        # Start session
        claude.start_session(
            repository_name="test-repo",
            repository_owner="testorg",
        )
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/claude-agent/sessions")

        # Get session
        claude.get_session("sess-1")
        req = session.requests[-1]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.test.local/claude-agent/sessions/sess-1")

    def test_delegate_repository_setup(self):
        """Verify delegate_repository_setup helper."""
        client, session = make_client({"session": {"id": "sess-2"}})
        claude = ClaudeAutomationClient(client)

        result = claude.delegate_repository_setup(
            repository_name="target-repo",
            repository_url="https://github.com/org/target-repo",
        )

        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        # Should use default integration tasks
        self.assertIsNotNone(req["json"].get("tasks"))

    def test_session_logging(self):
        """Verify session logging."""
        client, session = make_client({"logged": True})
        claude = ClaudeAutomationClient(client)

        claude.log("sess-1", message="Integration started", level="info")
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/claude-agent/sessions/sess-1/logs")

    def test_task_updates(self):
        """Verify task update operations."""
        client, session = make_client({"task": {"id": "task-1"}})
        claude = ClaudeAutomationClient(client)

        claude.update_task("sess-1", "task-1", status="completed", progress=1.0)
        req = session.requests[-1]
        self.assertEqual(req["method"], "PATCH")
        self.assertEqual(
            req["url"], "https://api.test.local/claude-agent/sessions/sess-1/tasks/task-1"
        )

    def test_integration_plan_storage(self):
        """Verify integration plan storage."""
        client, session = make_client({"plan": {"id": "plan-1"}})
        claude = ClaudeAutomationClient(client)

        claude.store_integration_plan(
            repository={"name": "test-repo"},
            recommendations="Add GraphRAG support",
            confidence_score=0.95,
        )
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/claude/integration-plans")


class ComprehensiveIntegrationTest(unittest.TestCase):
    """End-to-end test verifying all layers work together."""

    def test_all_clients_accessible_from_main_import(self):
        """Verify all client classes are exported from main package."""
        from plexity_sdk import (
            ContextClient,
            MCPClient,
            TeamDelegationClient,
            IntegrationAutomationClient,
            ClaudeAutomationClient,
            InsightClient,
        )

        # All should be importable
        self.assertIsNotNone(ContextClient)
        self.assertIsNotNone(MCPClient)
        self.assertIsNotNone(TeamDelegationClient)
        self.assertIsNotNone(IntegrationAutomationClient)
        self.assertIsNotNone(ClaudeAutomationClient)
        self.assertIsNotNone(InsightClient)

    def test_client_composition_pattern(self):
        """Verify clients can be composed with base PlexityClient."""
        base, _ = make_client()

        # All specialized clients should accept base client
        context = ContextClient(base)
        mcp = MCPClient(base)
        delegation = TeamDelegationClient(base, team_id="team-1")
        automation = IntegrationAutomationClient(base)
        claude = ClaudeAutomationClient(base)
        insight = InsightClient(base)

        # All should be initialized
        self.assertIsNotNone(context)
        self.assertIsNotNone(mcp)
        self.assertIsNotNone(delegation)
        self.assertIsNotNone(automation)
        self.assertIsNotNone(claude)
        self.assertIsNotNone(insight)

    def test_graphrag_integration_still_present(self):
        """Verify existing GraphRAG functionality is preserved."""
        from plexity_sdk import GraphRAGClient

        client, session = make_client({"results": []})
        graphrag = GraphRAGClient(client)

        # Should still be able to search
        graphrag.search("test query")
        req = session.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.test.local/graphrag/search")


if __name__ == "__main__":
    unittest.main()
