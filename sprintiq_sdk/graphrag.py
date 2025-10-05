from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

from .client import SprintIQClient

__all__ = [
    "GraphRAGTelemetry",
    "ensure_microsoft_graphrag_runtime"
]


@dataclass
class GraphRAGTelemetryContext:
    org_id: str
    environment: str = "prod"
    triggered_by: Optional[str] = None
    workflow_execution_id: Optional[str] = None


class GraphRAGTelemetry:
    """Thin helper over :class:`SprintIQClient` for GraphRAG telemetry ingest."""

    def __init__(self, client: SprintIQClient, context: GraphRAGTelemetryContext) -> None:
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


def ensure_microsoft_graphrag_runtime(
    *,
    virtual_env: str = "graphrag_env",
    workspace: str = "graphrag_workspace",
    python_executable: Optional[str] = None,
    graphrag_version: Optional[str] = None,
    force_virtualenv: bool = False,
    force_workspace: bool = False,
    extra_packages: Optional[Sequence[str]] = None,
) -> None:
    """Provision a Microsoft GraphRAG runtime using pure Python tooling.

    Mirrors the Node.js helper for environments that prefer Python orchestration.
    """

    python_cmd = python_executable or sys.executable
    venv_path = Path(virtual_env).resolve()
    workspace_path = Path(workspace).resolve()

    if venv_path.exists() and force_virtualenv:
        shutil.rmtree(venv_path)
    if not venv_path.exists():
        subprocess.run([python_cmd, "-m", "venv", str(venv_path)], check=True)

    if sys.platform == "win32":
        python_bin = venv_path / "Scripts" / "python.exe"
        pip_bin = venv_path / "Scripts" / "pip.exe"
    else:
        python_bin = venv_path / "bin" / "python"
        pip_bin = venv_path / "bin" / "pip"

    # Upgrade pip and install GraphRAG
    subprocess.run([str(pip_bin), "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
    package = f"graphrag=={graphrag_version}" if graphrag_version else "graphrag"
    args = [str(pip_bin), "install", package]
    if extra_packages:
        args.extend(extra_packages)
    subprocess.run(args, check=True)

    if not workspace_path.exists() or force_workspace:
        workspace_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [str(python_bin), "-m", "graphrag", "init", "--workspace", str(workspace_path), "--non-interactive"],
            check=True,
            cwd=str(workspace_path)
        )

    # Basic smoke test
    subprocess.run([str(python_bin), "-c", "import graphrag"], check=True)
