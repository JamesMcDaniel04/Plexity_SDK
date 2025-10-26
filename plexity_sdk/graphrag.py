from __future__ import annotations

import os
import shutil
import subprocess
import sys
import asyncio
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
from .orchestration import (
    IncrementalJobHandle,
    IncrementalJobScheduler,
    IncrementalJobSpec,
    IncrementalJobStatus,
)
from .security import AccessControlPolicy, ComplianceDirective, EncryptionContext
from .storage import StorageAdapter, StorageAdapterRegistry, StorageObject

__all__ = [
    "GraphRAGClient",
    "GraphRAGTelemetry",
    "ensure_microsoft_graphrag_runtime",
]

_BACKEND_FEATURE_ENDPOINTS: Dict[GraphRAGFeature, Tuple[Tuple[str, str], ...]] = {
    GraphRAGFeature.INCREMENTAL_JOB_ADVISOR: (
        ("GET", "/graphrag/incremental/jobs/recommendations"),
        ("POST", "/graphrag/incremental/jobs"),
        ("POST", "/graphrag/incremental/jobs/slices"),
    ),
    GraphRAGFeature.ENTERPRISE_ADDONS: (
        ("POST", "/graphrag/compliance/directives"),
    ),
}


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
        graph_id: Optional[str] = None,
        shard_id: Optional[str] = None,
        access_policy: Optional[AccessControlPolicy] = None,
        encryption: Optional[EncryptionContext] = None,
        scheduler: Optional[IncrementalJobScheduler] = None,
        storage_registry: Optional[StorageAdapterRegistry] = None,
        default_storage_adapter: Optional[str] = None,
        validate_backend_support: bool = True,
    ) -> None:
        self._client = client
        self._org_id = org_id
        self._environment = environment
        self._team_id = team_id
        self._graph_id = graph_id
        self._shard_id = shard_id
        self._access_policy = access_policy
        self._encryption_context = encryption
        self._scheduler = scheduler
        self._storage_registry = storage_registry or StorageAdapterRegistry()
        self._default_storage_adapter = default_storage_adapter
        self._runtime_profile = runtime_profile or resolve_runtime_profile(
            package,
            enable=enable_features,
            disable=disable_features,
        )
        self._validate_backend_support = bool(validate_backend_support)
        self._feature_capabilities: Dict[GraphRAGFeature, bool] = {}
        if self._validate_backend_support:
            self.validate_backend_support(strict=True)

    @property
    def context(self) -> Dict[str, Optional[str]]:
        return {
            "org_id": self._org_id,
            "environment": self._environment,
            "team_id": self._team_id,
            "graph_id": self._graph_id,
            "shard_id": self._shard_id,
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

    @property
    def access_policy(self) -> Optional[AccessControlPolicy]:
        return self._access_policy

    @property
    def encryption_context(self) -> Optional[EncryptionContext]:
        return self._encryption_context

    @property
    def scheduler(self) -> Optional[IncrementalJobScheduler]:
        return self._scheduler

    @property
    def storage_registry(self) -> StorageAdapterRegistry:
        return self._storage_registry

    @property
    def default_storage_adapter(self) -> Optional[str]:
        return self._default_storage_adapter

    def set_scheduler(self, scheduler: IncrementalJobScheduler) -> None:
        self._scheduler = scheduler

    def set_access_policy(self, policy: Optional[AccessControlPolicy]) -> None:
        self._access_policy = policy

    def set_encryption_context(self, context: Optional[EncryptionContext]) -> None:
        self._encryption_context = context

    def set_default_storage_adapter(self, name: Optional[str]) -> None:
        self._default_storage_adapter = name

    def register_storage_adapter(self, name: str, adapter: StorageAdapter, *, override: bool = False) -> None:
        self._storage_registry.register(name, adapter, override=override)

    def get_storage_adapter(self, name: Optional[str] = None) -> StorageAdapter:
        target = name or self._default_storage_adapter
        if not target:
            raise RuntimeError("No storage adapter configured")
        return self._storage_registry.get(target)

    def update_context(
        self,
        *,
        org_id: Optional[str] = None,
        environment: Optional[str] = None,
        team_id: Optional[str] = None,
        graph_id: Optional[str] = None,
        shard_id: Optional[str] = None,
        access_policy: Optional[AccessControlPolicy] = None,
        encryption: Optional[EncryptionContext] = None,
        default_storage_adapter: Optional[str] = None,
    ) -> None:
        if org_id is not None:
            self._org_id = org_id
        if environment is not None:
            self._environment = environment
        if team_id is not None:
            self._team_id = team_id
        if graph_id is not None:
            self._graph_id = graph_id
        if shard_id is not None:
            self._shard_id = shard_id
        if access_policy is not None:
            self._access_policy = access_policy
        if encryption is not None:
            self._encryption_context = encryption
        if default_storage_adapter is not None:
            self._default_storage_adapter = default_storage_adapter

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
        if self._graph_id and "graph_id" not in merged:
            merged["graph_id"] = self._graph_id
        if self._shard_id and "shard_id" not in merged:
            merged["shard_id"] = self._shard_id
        if self._access_policy and "access_policy" not in merged:
            merged["access_policy"] = self._access_policy.to_dict()
        if self._encryption_context and "encryption" not in merged:
            merged["encryption"] = self._encryption_context.to_dict()
        return merged

    def offload_intermediate_state(
        self,
        key: str,
        data: Any,
        *,
        adapter: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageObject:
        payload = data if isinstance(data, bytes) else str(data).encode("utf-8")
        storage_adapter = self.get_storage_adapter(adapter)
        return storage_adapter.put_object(key, payload, metadata=metadata)

    def retrieve_intermediate_state(self, key: str, *, adapter: Optional[str] = None) -> StorageObject:
        storage_adapter = self.get_storage_adapter(adapter)
        return storage_adapter.get_object(key)

    def delete_intermediate_state(self, key: str, *, adapter: Optional[str] = None) -> None:
        storage_adapter = self.get_storage_adapter(adapter)
        storage_adapter.delete_object(key)

    def _require_feature(self, feature: GraphRAGFeature) -> None:
        if not self.feature_flags.is_enabled(feature):
            raise RuntimeError(
                f"Feature '{feature.value}' is not enabled for the current GraphRAG runtime profile"
            )
        if self._validate_backend_support and feature in _BACKEND_FEATURE_ENDPOINTS:
            supported = self._feature_capabilities.get(feature)
            if supported is None:
                self.validate_backend_support()
                supported = self._feature_capabilities.get(feature)
            if supported is False:
                raise RuntimeError(
                    f"GraphRAG backend does not expose the required endpoints for feature '{feature.value}'. "
                    "Disable backend validation or upgrade the orchestrator deployment to use this feature."
                )

    def validate_backend_support(self, *, strict: bool = False) -> Dict[GraphRAGFeature, bool]:
        """Probe the orchestrator to confirm feature-dependent routes exist."""

        probe = getattr(self._client, "probe_endpoint", None)
        if not callable(probe):
            if strict:
                raise RuntimeError(
                    "The underlying client does not support backend capability probing. "
                    "Pass validate_backend_support=False or upgrade to a newer PlexityClient."
                )
            return {}

        capabilities: Dict[GraphRAGFeature, bool] = {}
        for feature, endpoints in _BACKEND_FEATURE_ENDPOINTS.items():
            supported = True
            for method, path in endpoints:
                if probe("OPTIONS", path):
                    continue
                if not probe(method, path):
                    supported = False
                    break
            capabilities[feature] = supported
            self._feature_capabilities[feature] = supported

        if strict:
            missing = sorted(
                feature.value for feature, ok in capabilities.items() if not ok and self.feature_flags.is_enabled(feature)
            )
            if missing:
                raise RuntimeError(
                    "GraphRAG backend is missing required endpoints for: " + ", ".join(missing)
                )
        return capabilities

    def _require_scheduler(self) -> IncrementalJobScheduler:
        if self._scheduler is None:
            raise RuntimeError("No incremental job scheduler configured")
        return self._scheduler

    def _run_blocking(self, coro: Any):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "An event loop is already running. Call the async variant (e.g., schedule_incremental_job_async)."
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

    def schedule_incremental_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> IncrementalJobHandle:
        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        scheduler = self._require_scheduler()
        spec = IncrementalJobSpec(
            job_type=job_type,
            payload=self._merge_context(dict(payload)),
            idempotency_key=idempotency_key,
            tags={str(k): str(v) for k, v in (tags or {}).items()},
        )
        return self._run_blocking(scheduler.schedule(spec))

    async def schedule_incremental_job_async(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> IncrementalJobHandle:
        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        scheduler = self._require_scheduler()
        spec = IncrementalJobSpec(
            job_type=job_type,
            payload=self._merge_context(dict(payload)),
            idempotency_key=idempotency_key,
            tags={str(k): str(v) for k, v in (tags or {}).items()},
        )
        return await scheduler.schedule(spec)

    def get_scheduled_job_status(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        scheduler = self._require_scheduler()
        return self._run_blocking(scheduler.get_status(handle))

    async def get_scheduled_job_status_async(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        scheduler = self._require_scheduler()
        return await scheduler.get_status(handle)

    def cancel_scheduled_job(self, handle: IncrementalJobHandle) -> None:
        scheduler = self._require_scheduler()
        self._run_blocking(scheduler.cancel(handle))

    async def cancel_scheduled_job_async(self, handle: IncrementalJobHandle) -> None:
        scheduler = self._require_scheduler()
        await scheduler.cancel(handle)

    def create_incremental_job(
        self,
        payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        job_labels: Optional[Iterable[str]] = None,
    ) -> Any:
        """Create a new incremental job with orchestrator-managed batching."""

        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        merged = self._merge_context(dict(payload))
        if idempotency_key is not None:
            merged["idempotency_key"] = idempotency_key
        if job_labels is not None:
            merged["job_labels"] = list(job_labels)
        return self._client.create_graphrag_incremental_job(**merged)

    def trigger_incremental_job_slice(
        self,
        slice_payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Trigger a specific incremental job slice."""

        self._require_feature(GraphRAGFeature.INCREMENTAL_JOB_ADVISOR)
        merged = self._merge_context(dict(slice_payload))
        if idempotency_key is not None:
            merged["idempotency_key"] = idempotency_key
        return self._client.trigger_graphrag_incremental_job_slice(**merged)

    def apply_compliance_directive(self, directive: ComplianceDirective) -> Any:
        self._require_feature(GraphRAGFeature.ENTERPRISE_ADDONS)
        merged = self._merge_context({})
        return self._client.apply_graphrag_compliance_directive(directive=directive.to_dict(), **merged)

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
