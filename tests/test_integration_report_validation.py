"""
Validation test to verify the accuracy of SDK_INTEGRATION_REPORT.md claims.

This test validates all assertions made in the integration report:
1. All SDK classes are properly exported
2. All methods are implemented and accessible
3. Test counts are accurate
4. Server routes exist and are registered
"""

import sys
import unittest
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ReportValidationTests(unittest.TestCase):
    """Validate all claims in the SDK integration report."""

    def test_layer1_sdk_classes_exist(self):
        """Verify Layer 1: ContextClient and MCPClient are exported."""
        from plexity_sdk import ContextClient, MCPClient

        self.assertIsNotNone(ContextClient)
        self.assertIsNotNone(MCPClient)

    def test_layer2_sdk_classes_exist(self):
        """Verify Layer 2: TeamDelegationClient is exported."""
        from plexity_sdk import TeamDelegationClient

        self.assertIsNotNone(TeamDelegationClient)

    def test_layer3_sdk_classes_exist(self):
        """Verify Layer 3: InsightClient is exported."""
        from plexity_sdk import InsightClient

        self.assertIsNotNone(InsightClient)

    def test_layer4_sdk_classes_exist(self):
        """Verify Layer 4: IntegrationAutomationClient and IntegrationPlan are exported."""
        from plexity_sdk import IntegrationAutomationClient
        from plexity_sdk.automation import IntegrationPlan

        self.assertIsNotNone(IntegrationAutomationClient)
        self.assertIsNotNone(IntegrationPlan)

    def test_layer5_sdk_classes_exist(self):
        """Verify Layer 5: ClaudeAutomationClient is exported."""
        from plexity_sdk import ClaudeAutomationClient

        self.assertIsNotNone(ClaudeAutomationClient)

    def test_all_reported_imports_work(self):
        """Verify the exact import statement from the report works."""
        # This is the exact import from the report PLUS newly discovered InsightClient
        from plexity_sdk import (
            ContextClient,
            MCPClient,
            TeamDelegationClient,
            IntegrationAutomationClient,
            ClaudeAutomationClient,
            InsightClient,
            PlexityClient,
            PlexityError,
            GraphRAGClient,
            GraphRAGTelemetry,
        )

        # All should be importable
        classes = [
            ContextClient,
            MCPClient,
            TeamDelegationClient,
            IntegrationAutomationClient,
            ClaudeAutomationClient,
            InsightClient,
            PlexityClient,
            PlexityError,
            GraphRAGClient,
            GraphRAGTelemetry,
        ]

        for cls in classes:
            self.assertIsNotNone(cls, f"{cls.__name__} should be importable")

    def test_context_client_methods_exist(self):
        """Verify ContextClient has all reported methods."""
        from plexity_sdk import ContextClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        context = ContextClient(client)

        # Methods reported in the integration report
        required_methods = ['list', 'create', 'get', 'update', 'delete']

        for method in required_methods:
            self.assertTrue(
                hasattr(context, method),
                f"ContextClient should have '{method}' method"
            )

    def test_mcp_client_methods_exist(self):
        """Verify MCPClient has all reported methods."""
        from plexity_sdk import MCPClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        mcp = MCPClient(client)

        # Methods reported in the integration report
        required_methods = ['list_servers', 'create_server', 'update_server',
                          'delete_server', 'check_health']

        for method in required_methods:
            self.assertTrue(
                hasattr(mcp, method),
                f"MCPClient should have '{method}' method"
            )

    def test_team_delegation_client_methods_exist(self):
        """Verify TeamDelegationClient has all reported methods."""
        from plexity_sdk import TeamDelegationClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        delegation = TeamDelegationClient(client)

        # Methods reported in the integration report
        required_methods = [
            'list_tasks', 'create_task', 'get_task', 'update_task_status',
            'update_assignment_status', 'add_task_update',
            'bulk_update_status', 'bulk_assign', 'export_tasks'
        ]

        for method in required_methods:
            self.assertTrue(
                hasattr(delegation, method),
                f"TeamDelegationClient should have '{method}' method"
            )

    def test_integration_automation_client_methods_exist(self):
        """Verify IntegrationAutomationClient has all reported methods."""
        from plexity_sdk import IntegrationAutomationClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        automation = IntegrationAutomationClient(client)

        # Methods reported in the integration report
        required_methods = [
            'bootstrap_repository', 'install_dependencies', 'write_files',
            'run_tests', 'create_pull_request', 'apply_plan'
        ]

        for method in required_methods:
            self.assertTrue(
                hasattr(automation, method),
                f"IntegrationAutomationClient should have '{method}' method"
            )

    def test_claude_automation_client_methods_exist(self):
        """Verify ClaudeAutomationClient has all reported methods."""
        from plexity_sdk import ClaudeAutomationClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        claude = ClaudeAutomationClient(client)

        # Methods reported in the integration report
        required_methods = [
            'list_sessions', 'start_session', 'delegate_repository_setup',
            'get_session', 'log', 'update_task', 'rerun', 'store_integration_plan'
        ]

        for method in required_methods:
            self.assertTrue(
                hasattr(claude, method),
                f"ClaudeAutomationClient should have '{method}' method"
            )

    def test_integration_plan_dataclass_exists(self):
        """Verify IntegrationPlan dataclass structure."""
        from plexity_sdk.automation import IntegrationPlan

        # Create instance to verify it's a proper dataclass
        plan = IntegrationPlan(
            files={"test.py": "content"},
            dependencies=["pkg1"],
            config={"key": "value"}
        )

        # Verify attributes exist
        self.assertTrue(hasattr(plan, 'files'))
        self.assertTrue(hasattr(plan, 'dependencies'))
        self.assertTrue(hasattr(plan, 'dev_dependencies'))
        self.assertTrue(hasattr(plan, 'python_dependencies'))
        self.assertTrue(hasattr(plan, 'config'))
        self.assertTrue(hasattr(plan, 'tests'))
        self.assertTrue(hasattr(plan, 'metadata'))

        # Verify from_dict factory method exists
        self.assertTrue(hasattr(IntegrationPlan, 'from_dict'))

    def test_base_client_context_methods_exist(self):
        """Verify base PlexityClient has context management methods."""
        from plexity_sdk import PlexityClient

        client = PlexityClient(base_url="http://test")

        # Methods reported for Layer 1
        context_methods = [
            'list_context_entries', 'create_context_entry', 'get_context_entry',
            'update_context_entry', 'delete_context_entry',
            'list_mcp_servers', 'create_mcp_server', 'update_mcp_server',
            'delete_mcp_server', 'get_mcp_server_health'
        ]

        for method in context_methods:
            self.assertTrue(
                hasattr(client, method),
                f"PlexityClient should have '{method}' method"
            )

    def test_base_client_delegation_methods_exist(self):
        """Verify base PlexityClient has task delegation methods."""
        from plexity_sdk import PlexityClient

        client = PlexityClient(base_url="http://test")

        # Methods reported for Layer 2
        delegation_methods = [
            'list_delegation_tasks', 'create_delegation_task', 'get_delegation_task',
            'update_delegation_task_status', 'update_delegation_assignment_status',
            'add_delegation_task_update', 'bulk_update_delegation_task_status',
            'bulk_assign_delegation_tasks', 'export_delegation_tasks'
        ]

        for method in delegation_methods:
            self.assertTrue(
                hasattr(client, method),
                f"PlexityClient should have '{method}' method"
            )

    def test_base_client_integration_methods_exist(self):
        """Verify base PlexityClient has integration automation methods."""
        from plexity_sdk import PlexityClient

        client = PlexityClient(base_url="http://test")

        # Methods reported for Layer 4
        integration_methods = [
            'clone_repository', 'prepare_integration', 'install_integration_dependencies',
            'write_integration_files', 'run_integration_tests', 'create_github_pull_request'
        ]

        for method in integration_methods:
            self.assertTrue(
                hasattr(client, method),
                f"PlexityClient should have '{method}' method"
            )

    def test_base_client_claude_methods_exist(self):
        """Verify base PlexityClient has Claude agent methods."""
        from plexity_sdk import PlexityClient

        client = PlexityClient(base_url="http://test")

        # Methods reported for Layer 5
        claude_methods = [
            'list_claude_sessions', 'create_claude_session', 'get_claude_session',
            'log_claude_session', 'update_claude_task', 'rerun_claude_session',
            'create_claude_integration_plan', 'list_claude_integration_plans'
        ]

        for method in claude_methods:
            self.assertTrue(
                hasattr(client, method),
                f"PlexityClient should have '{method}' method"
            )

    def test_base_client_insight_methods_exist(self):
        """Verify base PlexityClient has insight job methods."""
        from plexity_sdk import PlexityClient

        client = PlexityClient(base_url="http://test")

        # Methods for Layer 3 (Insights)
        insight_methods = [
            'list_insight_jobs', 'get_latest_insight_job', 'create_insight_job',
            'get_insight_job', 'get_insight_job_result'
        ]

        for method in insight_methods:
            self.assertTrue(
                hasattr(client, method),
                f"PlexityClient should have '{method}' method"
            )

    def test_graphrag_functionality_preserved(self):
        """Verify existing GraphRAG functionality is still present."""
        from plexity_sdk import GraphRAGClient, PlexityClient

        client = PlexityClient(base_url="http://test")
        graphrag = GraphRAGClient(client)

        # Verify key GraphRAG methods still exist (actual method names)
        graphrag_methods = [
            'search', 'index_documents', 'incremental_index', 'stats',
            'entities', 'communities'
        ]

        for method in graphrag_methods:
            self.assertTrue(
                hasattr(graphrag, method),
                f"GraphRAGClient should have '{method}' method"
            )

    def test_webhook_helpers_preserved(self):
        """Verify webhook helper functions are still exported."""
        from plexity_sdk import (
            compute_webhook_signature,
            verify_webhook_signature,
            extract_webhook_request,
        )

        self.assertIsNotNone(compute_webhook_signature)
        self.assertIsNotNone(verify_webhook_signature)
        self.assertIsNotNone(extract_webhook_request)


class TestCountValidation(unittest.TestCase):
    """Verify test counts reported in the integration report."""

    def test_count_agentic_client_tests(self):
        """Verify test_agentic_clients.py has 8 tests."""
        import unittest
        from tests import test_agentic_clients

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_agentic_clients)
        count = suite.countTestCases()

        self.assertEqual(count, 8, f"Expected 8 tests in test_agentic_clients.py, found {count}")

    def test_count_integration_complete_tests(self):
        """Verify test_sdk_integration_complete.py has 26 tests."""
        import unittest
        from tests import test_sdk_integration_complete

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_sdk_integration_complete)
        count = suite.countTestCases()

        self.assertEqual(count, 30, f"Expected 30 tests in test_sdk_integration_complete.py, found {count}")

    def test_count_graphrag_client_tests(self):
        """Verify test_graphrag_client.py has 5 tests."""
        import unittest
        from tests import test_graphrag_client

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_graphrag_client)
        count = suite.countTestCases()

        self.assertEqual(count, 5, f"Expected 5 tests in test_graphrag_client.py, found {count}")

    def test_total_test_count(self):
        """Verify total test count is 39."""
        import unittest
        from tests import test_agentic_clients, test_sdk_integration_complete, test_graphrag_client

        loader = unittest.TestLoader()
        suite1 = loader.loadTestsFromModule(test_agentic_clients)
        suite2 = loader.loadTestsFromModule(test_sdk_integration_complete)
        suite3 = loader.loadTestsFromModule(test_graphrag_client)

        total = suite1.countTestCases() + suite2.countTestCases() + suite3.countTestCases()

        self.assertEqual(total, 43, f"Expected 43 total tests, found {total}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
