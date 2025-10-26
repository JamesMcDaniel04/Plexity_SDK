from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Protocol, runtime_checkable

__all__ = [
    "JobState",
    "IncrementalJobSpec",
    "IncrementalJobHandle",
    "IncrementalJobStatus",
    "IncrementalJobScheduler",
    "InMemoryJobScheduler",
    "TemporalJobScheduler",
    "ArgoWorkflowsScheduler",
]


class JobState(str, Enum):
    """Lifecycle states for incremental job orchestration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class IncrementalJobSpec:
    """Specification for a long-running incremental job."""

    job_type: str
    payload: Dict[str, Any]
    idempotency_key: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IncrementalJobHandle:
    """Scheduler-specific handle for referencing a job."""

    reference: str
    scheduler: str


@dataclass
class IncrementalJobStatus:
    """Status for a scheduled incremental job."""

    state: JobState
    reference: str
    scheduler: str
    details: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IncrementalJobScheduler(Protocol):
    """Protocol for pluggable job schedulers."""

    name: str

    async def schedule(self, spec: IncrementalJobSpec) -> IncrementalJobHandle:
        ...

    async def get_status(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        ...

    async def cancel(self, handle: IncrementalJobHandle) -> None:
        ...


class InMemoryJobScheduler:
    """In-memory scheduler useful for tests and local development."""

    def __init__(self) -> None:
        self.name = "in-memory"
        self._jobs: Dict[str, IncrementalJobStatus] = {}

    async def schedule(self, spec: IncrementalJobSpec) -> IncrementalJobHandle:
        reference = spec.idempotency_key or f"in-memory-{len(self._jobs)+1}"
        handle = IncrementalJobHandle(reference=reference, scheduler=self.name)
        if reference not in self._jobs:
            self._jobs[reference] = IncrementalJobStatus(
                state=JobState.PENDING,
                reference=reference,
                scheduler=self.name,
                details={"payload": spec.payload, "tags": spec.tags},
            )
        return handle

    async def get_status(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        if handle.reference not in self._jobs:
            raise KeyError(f"Job '{handle.reference}' is not managed by this scheduler")
        return self._jobs[handle.reference]

    async def cancel(self, handle: IncrementalJobHandle) -> None:
        status = await self.get_status(handle)
        status.state = JobState.CANCELLED


def _require_temporal() -> Any:
    try:
        from temporalio.client import Client  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Install plexity-sdk[temporal] or plexity-sdk[enterprise] to use the Temporal scheduler integration"
        ) from exc
    return Client


class TemporalJobScheduler:
    """Temporal scheduler integration."""

    def __init__(
        self,
        *,
        target_host: str,
        namespace: str,
        task_queue: str,
        client: Any = None,
    ) -> None:
        Client = _require_temporal()
        self.name = "temporal"
        self._namespace = namespace
        self._task_queue = task_queue
        self._client = client
        self._target_host = target_host
        self._client_kwargs: Dict[str, Any] = {}
        if client is None:
            self._client_kwargs["target_host"] = target_host

        # Lazy client; TemporalClient is async.
        self._temporal_client: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._temporal_client is not None:
            return self._temporal_client
        Client = _require_temporal()
        if self._client:
            self._temporal_client = self._client
        else:
            self._temporal_client = await Client.connect(**self._client_kwargs, namespace=self._namespace)
        return self._temporal_client

    async def schedule(self, spec: IncrementalJobSpec) -> IncrementalJobHandle:
        client = await self._get_client()
        workflow_id = spec.idempotency_key or f"graphrag-incremental-{spec.job_type}"
        await client.start_workflow(
            spec.job_type,
            spec.payload,
            id=workflow_id,
            task_queue=self._task_queue,
            start_timeout=spec.payload.get("start_timeout"),
        )
        return IncrementalJobHandle(reference=workflow_id, scheduler=self.name)

    async def get_status(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        client = await self._get_client()
        workflow = client.get_workflow_handle(handle.reference)
        desc = await workflow.describe()
        state = JobState.RUNNING
        if desc.close_time:
            if desc.status.name.lower() == "completed":
                state = JobState.SUCCEEDED
            elif desc.status.name.lower() == "terminated":
                state = JobState.CANCELLED
            else:
                state = JobState.FAILED
        return IncrementalJobStatus(
            state=state,
            reference=handle.reference,
            scheduler=self.name,
            details={
                "history_length": desc.history_length,
                "memo": desc.memo,
                "status": desc.status.name,
            },
        )

    async def cancel(self, handle: IncrementalJobHandle) -> None:
        client = await self._get_client()
        workflow = client.get_workflow_handle(handle.reference)
        await workflow.terminate("Cancelled via SDK")


def _require_requests() -> Any:
    try:
        import requests  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("Install plexity-sdk[argo] or plexity-sdk[enterprise] to use the Argo scheduler") from exc
    return requests


class ArgoWorkflowsScheduler:
    """Argo Workflows scheduler integration via REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        namespace: str = "default",
        token: Optional[str] = None,
        verify_ssl: bool = True,
    ) -> None:
        self.name = "argo"
        self._base_url = base_url.rstrip("/")
        self._namespace = namespace
        self._token = token
        self._verify_ssl = verify_ssl
        self._requests = _require_requests()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def schedule(self, spec: IncrementalJobSpec) -> IncrementalJobHandle:
        payload = {
            "namespace": self._namespace,
            "workflowTemplateRef": {"name": spec.job_type},
            "arguments": {"parameters": [{"name": k, "value": str(v)} for k, v in spec.payload.items()]},
        }
        if spec.idempotency_key:
            payload.setdefault("metadata", {})["generateName"] = spec.idempotency_key
        resp = self._requests.post(
            f"{self._base_url}/api/v1/workflows/{self._namespace}",
            json=payload,
            headers=self._headers(),
            verify=self._verify_ssl,
        )
        resp.raise_for_status()
        body = resp.json()
        reference = body.get("metadata", {}).get("name")
        if not reference:
            raise RuntimeError("Argo workflow submission did not return a workflow name")
        return IncrementalJobHandle(reference=reference, scheduler=self.name)

    async def get_status(self, handle: IncrementalJobHandle) -> IncrementalJobStatus:
        resp = self._requests.get(
            f"{self._base_url}/api/v1/workflows/{self._namespace}/{handle.reference}",
            headers=self._headers(),
            verify=self._verify_ssl,
        )
        resp.raise_for_status()
        body = resp.json()
        phase = body.get("status", {}).get("phase", "Unknown").lower()
        mapping = {
            "succeeded": JobState.SUCCEEDED,
            "failed": JobState.FAILED,
            "error": JobState.FAILED,
            "running": JobState.RUNNING,
            "pending": JobState.PENDING,
        }
        state = mapping.get(phase, JobState.RUNNING)
        return IncrementalJobStatus(
            state=state,
            reference=handle.reference,
            scheduler=self.name,
            details={"phase": phase, "progress": body.get("status", {}).get("progress")},
        )

    async def cancel(self, handle: IncrementalJobHandle) -> None:
        resp = self._requests.put(
            f"{self._base_url}/api/v1/workflows/{self._namespace}/{handle.reference}/terminate",
            headers=self._headers(),
            verify=self._verify_ssl,
        )
        resp.raise_for_status()
