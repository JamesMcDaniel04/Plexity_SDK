from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .client import PlexityClient
from .graphrag_runtime import (
    GraphRAGFeature,
    GraphRAGFeatureFlags,
    GraphRAGPackage,
    GraphRAGRuntimeProfile,
    resolve_runtime_profile,
)
from .neo4j import (
    JobSliceRecommendation,
    Neo4jConnectionConfig,
    Neo4jDriverManager,
    Neo4jIncrementalJobAdvisor,
    Neo4jMigrationPlan,
    Neo4jSchemaPlanner,
    Neo4jSchemaSnapshot,
    Neo4jTransactionalBatchExecutor,
)

__all__ = [
    "GraphRAGClient",
    "GraphRAGTelemetry",
    "ensure_microsoft_graphrag_runtime",
]


@dataclass
class GraphRAGTelemetryContext:
    org_id: str
    environment: str = "prod"
    triggered_by: Optional[str] = None
    workflow_execution_id: Optional[str] = None


class GraphRAGTelemetry:
    """Thin helper over :class:`PlexityClient` for GraphRAG telemetry ingest."""

    def __init__(self, client: PlexityClient, context: GraphRAGTelemetryContext) -> None:
        self._client = client
        self._context = context

    def update_context(self, **kwargs: Any) -> None:
        if "org_id" in kwargs:
            self._context.org_id = kwargs["org_id"]
        if "environment" in kwargs:
            self._context.environment = kwargs["environment"]
        if "triggered_by" in kwargs:
            self._context.triggered_by = kwargs["triggered_by"]
        if "workflow_execution_id" in kwargs:
            self._context.workflow_execution_id = kwargs["workflow_execution_id"]

    def record_entity_events(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e) for e in events]
        return self._client.record_graphrag_entity_events(payload)

    def record_relationship_events(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e) for e in events]
        return self._client.record_graphrag_relationship_events(payload)

    def record_community_events(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e) for e in events]
        return self._client.record_graphrag_community_events(payload)

    def record_query_coverage(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e, include_trigger=False) for e in events]
        return self._client.record_graphrag_query_coverage(payload)

    def record_indexing_operations(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e) for e in events]
        return self._client.record_graphrag_indexing_operations(payload)

    def record_schema_snapshots(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e, include_trigger=False) for e in events]
        return self._client.record_graphrag_schema_snapshots(payload)

    def record_topology_snapshots(self, events: Iterable[Dict[str, Any]]) -> int:
        payload = [self._decorate(e, include_trigger=False) for e in events]
        return self._client.record_graphrag_topology_snapshots(payload)

    def _decorate(self, event: Dict[str, Any], *, include_trigger: bool = True) -> Dict[str, Any]:
        enriched = dict(event)
        enriched.setdefault("orgId", self._context.org_id)
        enriched.setdefault("environment", self._context.environment)
        if include_trigger:
            if "triggeredBy" not in enriched and self._context.triggered_by:
                enriched["triggeredBy"] = self._context.triggered_by
            if "workflowExecutionId" not in enriched and self._context.workflow_execution_id:
                enriched["workflowExecutionId"] = self._context.workflow_execution_id
        return enriched


class GraphRAGClient:
    """Convenience wrapper around :class:`PlexityClient` for GraphRAG operations."""

    def __init__(
        self,
        client: PlexityClient,
        *,
        org_id: Optional[str] = None,
        environment: str = "prod",
        team_id: Optional[str] = None,
        runtime_profile: Optional[GraphRAGRuntimeProfile] = None,
        package: GraphRAGPackage | str = GraphRAGPackage.CORE,
        enable_features: Optional[Iterable[GraphRAGFeature | str]] = None,
        disable_features: Optional[Iterable[GraphRAGFeature | str]] = None,
    ) -> None:
        self._client = client
        self._org_id = org_id
        self._environment = environment
        self._team_id = team_id
        self._runtime_profile = runtime_profile or resolve_runtime_profile(
            package,
            enable=enable_features,
            disable=disable_features,
        )

    @property
    def context(self) -> Dict[str, Optional[str]]:
        return {
            "org_id": self._org_id,
            "environment": self._environment,
            "team_id": self._team_id,
        }

    @property
    def runtime_profile(self) -> GraphRAGRuntimeProfile:
        return self._runtime_profile

    @property
    def feature_flags(self) -> GraphRAGFeatureFlags:
        return self._runtime_profile.feature_flags

    @property
    def optional_dependencies(self) -> Tuple[str, ...]:
        return tuple(sorted(self._runtime_profile.optional_dependencies))

    def update_context(
        self,
        *,
        org_id: Optional[str] = None,
        environment: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> None:
        if org_id is not None:
            self._org_id = org_id
        if environment is not None:
            self._environment = environment
        if team_id is not None:
            self._team_id = team_id

    def search(self, query: str, **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.search_graphrag(query, **merged)

    def index_documents(self, documents: Iterable[Dict[str, Any]], **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.index_graphrag(documents, **merged)

    def incremental_index(self, documents: Iterable[Dict[str, Any]], **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.incremental_index_graphrag(documents, **merged)

    def stats(self, **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.get_graphrag_stats(**merged)

    def entities(self, **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.get_graphrag_entities(**merged)

    def communities(self, **options: Any) -> Any:
        merged = self._merge_context(options)
        return self._client.get_graphrag_communities(**merged)

    def _merge_context(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(overrides or {})
        if self._org_id and "org_id" not in merged:
            merged["org_id"] = self._org_id
        if self._environment and "environment" not in merged:
            merged["environment"] = self._environment
        if self._team_id is not None and "team_id" not in merged:
            merged["team_id"] = self._team_id
        return merged

    def _require_feature(self, feature: GraphRAGFeature) -> None:
        if not self.feature_flags.is_enabled(feature):
            raise RuntimeError(
                f"Feature '{feature.value}' is not enabled for the current GraphRAG runtime profile"
            )

    # ------------------------------------------------------------------ Incremental Jobs
    def recommend_incremental_job_slices(
        self,
        *,
        labels: Optional[Iterable[str]] = None,
        org_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        """Return incremental job slice recommendations from the orchestrator."""

        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        payload: Dict[str, Any] = {}
        if labels is not None:
            payload["labels"] = list(labels)
        if org_id is not None:
            payload["org_id"] = org_id
        if limit is not None:
            payload["limit"] = int(limit)
        merged = self._merge_context(payload)
        return self._client.recommend_graphrag_job_slices(**merged)

    def create_incremental_job(self, payload: Dict[str, Any]) -> Any:
        """Create a new incremental job with orchestrator-managed batching."""

        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        merged = self._merge_context(dict(payload))
        return self._client.create_graphrag_incremental_job(**merged)

    def trigger_incremental_job_slice(self, slice_payload: Dict[str, Any]) -> Any:
        """Trigger a specific incremental job slice."""

        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        merged = self._merge_context(dict(slice_payload))
        return self._client.trigger_graphrag_incremental_job_slice(**merged)

    # ------------------------------------------------------------------ Neo4j helpers
    def create_neo4j_driver_manager(self, config: Neo4jConnectionConfig) -> Neo4jDriverManager:
        self._require_feature(GraphRAGFeature.NEO4J_SUPPORT)
        return Neo4jDriverManager(config)

    def create_neo4j_schema_planner(self, manager: Neo4jDriverManager) -> Neo4jSchemaPlanner:
        self._require_feature(GraphRAGFeature.SCHEMA_DIFF)
        return Neo4jSchemaPlanner(manager)

    def create_neo4j_batch_executor(
        self,
        manager: Neo4jDriverManager,
        *,
        batch_size: int = 50,
    ) -> Neo4jTransactionalBatchExecutor:
        self._require_feature(GraphRAGFeature.SCHEMA_DIFF)
        return Neo4jTransactionalBatchExecutor(manager, batch_size=batch_size)

    def recommend_neo4j_job_slices(
        self,
        manager: Neo4jDriverManager,
        *,
        labels: Optional[Iterable[str]] = None,
        limit: int = 25,
    ) -> List[JobSliceRecommendation]:
        self._require_feature(GraphRAGFeature.NEO4J_SUPPORT)
        advisor = Neo4jIncrementalJobAdvisor(manager)
        return advisor.recommend(labels=list(labels) if labels else None, limit=limit)

    def snapshot_neo4j_schema(self, planner: Neo4jSchemaPlanner) -> Neo4jSchemaSnapshot:
        self._require_feature(GraphRAGFeature.SCHEMA_DIFF)
        return planner.snapshot()

    def plan_neo4j_schema_migration(
        self,
        planner: Neo4jSchemaPlanner,
        target: Neo4jSchemaSnapshot,
        *,
        current: Optional[Neo4jSchemaSnapshot] = None,
    ) -> Neo4jMigrationPlan:
        self._require_feature(GraphRAGFeature.SCHEMA_DIFF)
        return planner.plan_migration(target, current=current)

    def apply_neo4j_schema_migration(
        self,
        executor: Neo4jTransactionalBatchExecutor,
        plan: Neo4jMigrationPlan,
        *,
        dry_run: bool = False,
    ) -> Any:
        self._require_feature(GraphRAGFeature.SCHEMA_DIFF)
        return executor.run_plan(plan, dry_run=dry_run)

    # ------------------------------------------------------------------ Plugin Entry Point
    def ingest_with_plugin(self, plugin_name: str, slice_payload: Dict[str, Any]) -> Any:
        """Invoke an incremental ingestion plugin."""

        self._require_feature(GraphRAGFeature.PLUGIN_ENTRYPOINTS)
        from .incremental_plugins import invoke_incremental_ingestion_plugin

        return invoke_incremental_ingestion_plugin(plugin_name, self, slice_payload)


def ensure_microsoft_graphrag_runtime(
    *,
    virtual_env: str = "graphrag_env",
    workspace: str = "graphrag_workspace",
    python_executable: Optional[str] = None,
    graphrag_version: Optional[str] = None,
    force_virtualenv: bool = False,
    force_workspace: bool = False,
    extra_packages: Optional[Sequence[str]] = None,
    skip_if_installed: bool = True,
    logger: Optional[Callable[[str], None]] = None,
    verbose: bool = False,
) -> None:
    """Provision a Microsoft GraphRAG runtime using pure Python tooling.

    Mirrors the Node.js helper for environments that prefer Python orchestration.
    """

    python_cmd = python_executable or sys.executable
    venv_path = Path(virtual_env).resolve()
    workspace_path = Path(workspace).resolve()

    def _log(message: str) -> None:
        if logger is not None:
            logger(message)
        elif verbose:
            print(f"[plexity-sdk] {message}")

    def _run(command: Sequence[str], *, cwd: Optional[str] = None) -> None:
        _log(f"Running: {' '.join(command)}")
        try:
            subprocess.run(command, check=True, cwd=cwd)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - surfaced in tests
            cmd = " ".join(command)
            raise RuntimeError(f"Command failed with exit code {exc.returncode}: {cmd}") from exc

    if venv_path.exists() and force_virtualenv:
        _log(f"Removing existing virtual environment at {venv_path}")
        shutil.rmtree(venv_path)
    if not venv_path.exists():
        _log(f"Creating virtual environment at {venv_path}")
        _run([python_cmd, "-m", "venv", str(venv_path)])

    if sys.platform == "win32":
        python_bin = venv_path / "Scripts" / "python.exe"
        pip_bin = venv_path / "Scripts" / "pip.exe"
    else:
        python_bin = venv_path / "bin" / "python"
        pip_bin = venv_path / "bin" / "pip"

    def _package_installed() -> bool:
        result = subprocess.run(
            [str(pip_bin), "show", "graphrag"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    should_install = True
    if skip_if_installed and _package_installed() and not force_virtualenv:
        should_install = False
        _log("Detected existing graphrag installation; skipping package install.")

    install_targets: List[str] = []
    package = f"graphrag=={graphrag_version}" if graphrag_version else "graphrag"
    if should_install:
        install_targets.append(package)
    if extra_packages:
        install_targets.extend(extra_packages)
    if install_targets:
        _run([str(pip_bin), "install", "--upgrade", "pip", "setuptools", "wheel"])
        _run([str(pip_bin), "install", *install_targets])

    if not workspace_path.exists() or force_workspace:
        _log(f"Initialising GraphRAG workspace at {workspace_path}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        _run(
            [str(python_bin), "-m", "graphrag", "init", "--workspace", str(workspace_path), "--non-interactive"],
            cwd=str(workspace_path),
        )

    # Basic smoke test
    _run([str(python_bin), "-c", "import graphrag"])
