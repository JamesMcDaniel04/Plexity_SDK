from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence

from .client import PlexityClient

__all__ = [
    "IntegrationPlan",
    "IntegrationAutomationClient",
    "ClaudeAutomationClient",
]


@dataclass
class IntegrationPlan:
    """Structured representation of an integration change-set."""

    files: Dict[str, Any] = field(default_factory=dict)
    dependencies: Sequence[str] = field(default_factory=tuple)
    dev_dependencies: Sequence[str] = field(default_factory=tuple)
    python_dependencies: Sequence[str] = field(default_factory=tuple)
    config: Optional[Dict[str, Any]] = None
    tests: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "IntegrationPlan":
        data = dict(payload or {})
        return cls(
            files=dict(data.get("files") or {}),
            dependencies=tuple(str(item) for item in data.get("dependencies", []) if str(item)),
            dev_dependencies=tuple(str(item) for item in data.get("dev_dependencies", []) if str(item)),
            python_dependencies=tuple(str(item) for item in data.get("python_dependencies", []) if str(item)),
            config=data.get("config"),
            tests=data.get("tests"),
            metadata=data.get("metadata"),
        )


class IntegrationAutomationClient:
    """High-level helper that orchestrates repository automation workflows."""

    def __init__(self, client: PlexityClient, *, auth_token: Optional[str] = None) -> None:
        self._client = client
        self._auth_token = auth_token

    def bootstrap_repository(
        self,
        *,
        repository_url: str,
        branch_name: Optional[str] = None,
        base_branch: str = "main",
        backup_original: bool = True,
        shallow_clone: bool = True,
        refresh_analysis: bool = False,
    ) -> Dict[str, Any]:
        clone_result = self._client.clone_repository(
            repository_url=repository_url,
            shallow_clone=shallow_clone,
            refresh_analysis=refresh_analysis,
            auth_token=self._auth_token,
        )
        prepare_result = self._client.prepare_integration(
            repository_url=repository_url,
            branch_name=branch_name,
            base_branch=base_branch,
            backup_original=backup_original,
            shallow_clone=shallow_clone,
            refresh_analysis=refresh_analysis,
            auth_token=self._auth_token,
        )
        repository_path = (
            prepare_result.get("local_path")
            or clone_result.get("local_path")
            or prepare_result.get("repository_path")
        )
        return {
            "clone": clone_result,
            "prepare": prepare_result,
            "repository_path": repository_path,
        }

    def install_dependencies(
        self,
        *,
        repository_path: str,
        dependencies: Sequence[str] = (),
        dev_dependencies: Sequence[str] = (),
        python_dependencies: Sequence[str] = (),
    ) -> Any:
        return self._client.install_integration_dependencies(
            repository_path=repository_path,
            dependencies=list(dependencies),
            dev_dependencies=list(dev_dependencies),
            python_dependencies=list(python_dependencies),
        )

    def write_files(
        self,
        *,
        repository_path: str,
        files: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        create_backup: bool = True,
    ) -> Any:
        return self._client.write_integration_files(
            repository_path=repository_path,
            files=files,
            create_backup=create_backup,
            config=config,
        )

    def run_tests(self, *, repository_path: str) -> Any:
        return self._client.run_integration_tests(repository_path=repository_path)

    def create_pull_request(
        self,
        *,
        repository_url: str,
        repository_path: str,
        branch_name: str,
        base_branch: str = "main",
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Any:
        return self._client.create_github_pull_request(
            repository_url=repository_url,
            repository_path=repository_path,
            branch_name=branch_name,
            base_branch=base_branch,
            title=title,
            body=body,
            auth_token=self._auth_token,
        )

    def apply_plan(
        self,
        *,
        repository_url: str,
        plan: IntegrationPlan | Dict[str, Any],
        branch_name: str = "graphrag-integration",
        base_branch: str = "main",
        pull_request_title: Optional[str] = None,
        pull_request_body: Optional[str] = None,
        run_tests: bool = True,
        backup_original: bool = True,
        shallow_clone: bool = True,
        refresh_analysis: bool = False,
        auto_pr: bool = True,
    ) -> Dict[str, Any]:
        resolved_plan = plan if isinstance(plan, IntegrationPlan) else IntegrationPlan.from_dict(plan)
        bootstrap = self.bootstrap_repository(
            repository_url=repository_url,
            branch_name=branch_name,
            base_branch=base_branch,
            backup_original=backup_original,
            shallow_clone=shallow_clone,
            refresh_analysis=refresh_analysis,
        )
        repo_path = bootstrap.get("repository_path")
        if not repo_path:
            raise RuntimeError("Repository path could not be resolved from bootstrap response")

        results: Dict[str, Any] = {"bootstrap": bootstrap}

        if any((resolved_plan.dependencies, resolved_plan.dev_dependencies, resolved_plan.python_dependencies)):
            results["dependencies"] = self.install_dependencies(
                repository_path=repo_path,
                dependencies=resolved_plan.dependencies,
                dev_dependencies=resolved_plan.dev_dependencies,
                python_dependencies=resolved_plan.python_dependencies,
            )

        if resolved_plan.files or resolved_plan.config:
            results["files"] = self.write_files(
                repository_path=repo_path,
                files=resolved_plan.files,
                config=resolved_plan.config,
            )

        if run_tests and (resolved_plan.tests is None or not resolved_plan.tests.get("skip")):
            results["tests"] = self.run_tests(repository_path=repo_path)

        if auto_pr:
            pr_title = pull_request_title or "Automated GraphRAG integration"
            pr_body = pull_request_body or resolved_plan.metadata.get("summary") if resolved_plan.metadata else None
            results["pull_request"] = self.create_pull_request(
                repository_url=repository_url,
                repository_path=repo_path,
                branch_name=branch_name,
                base_branch=base_branch,
                title=pr_title,
                body=pr_body,
            )

        return results


DEFAULT_INTEGRATION_TASKS: Sequence[Dict[str, Any]] = (
    {
        "name": "Assess existing GraphRAG readiness",
        "description": "Review repository structure, dependencies, and configuration to determine required GraphRAG integration steps.",
    },
    {
        "name": "Implement GraphRAG integration scaffolding",
        "description": "Add necessary configuration files, environment templates, and orchestrator calls to enable GraphRAG features.",
    },
    {
        "name": "Validate integration",
        "description": "Run project tests or GraphRAG smoke checks to confirm the integration works.",
    },
)


class ClaudeAutomationClient:
    """Convenience wrapper for Claude agent-driven integration support."""

    def __init__(self, client: PlexityClient) -> None:
        self._client = client

    def list_sessions(self, *, limit: Optional[int] = None, status: Optional[Iterable[str]] = None) -> Any:
        return self._client.list_claude_sessions(limit=limit, status=status)

    def start_session(
        self,
        *,
        repository_name: str,
        team_id: Optional[str] = None,
        repository_owner: Optional[str] = None,
        repository_url: Optional[str] = None,
        default_branch: Optional[str] = None,
        tasks: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> Any:
        return self._client.create_claude_session(
            repository_name=repository_name,
            team_id=team_id,
            repository_owner=repository_owner,
            repository_url=repository_url,
            default_branch=default_branch,
            tasks=tasks,
        )

    def delegate_repository_setup(
        self,
        *,
        repository_name: str,
        repository_owner: Optional[str] = None,
        repository_url: Optional[str] = None,
        team_id: Optional[str] = None,
        default_branch: Optional[str] = None,
        tasks: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> Any:
        task_payload = list(tasks) if tasks is not None else list(DEFAULT_INTEGRATION_TASKS)
        return self.start_session(
            repository_name=repository_name,
            team_id=team_id,
            repository_owner=repository_owner,
            repository_url=repository_url,
            default_branch=default_branch,
            tasks=task_payload,
        )

    def get_session(self, session_id: str) -> Any:
        return self._client.get_claude_session(session_id)

    def log(self, session_id: str, *, message: str, level: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Any:
        return self._client.log_claude_session(session_id, message=message, level=level, details=details)

    def update_task(
        self,
        session_id: str,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._client.update_claude_task(
            session_id,
            task_id,
            status=status,
            progress=progress,
            started_at=started_at,
            completed_at=completed_at,
            metadata=metadata,
        )

    def rerun(self, session_id: str) -> Any:
        return self._client.rerun_claude_session(session_id)

    def store_integration_plan(
        self,
        *,
        repository: Optional[Dict[str, Any]] = None,
        recommendations: Optional[str] = None,
        workflow: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._client.create_claude_integration_plan(
            repository=repository,
            recommendations=recommendations,
            workflow=workflow,
            confidence_score=confidence_score,
            metadata=metadata,
        )

