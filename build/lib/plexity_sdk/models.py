from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

__all__ = ["WorkflowSummary", "ExecutionSummary"]


@dataclass(frozen=True)
class WorkflowSummary:
    """Typed representation of a workflow returned by the Plexity API."""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkflowSummary":
        identifier = payload.get("id") or payload.get("workflow_id")
        if not identifier:
            raise ValueError("workflow payload is missing an 'id' field")
        return cls(
            id=str(identifier),
            name=payload.get("name"),
            description=payload.get("description"),
        )

    @classmethod
    def parse_many(cls, payload: Any) -> List["WorkflowSummary"]:
        items: Iterable[Any]
        if isinstance(payload, dict):
            items = payload.get("workflows") or payload.get("items") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        summaries: List[WorkflowSummary] = []
        for item in items:
            if isinstance(item, dict):
                try:
                    summaries.append(cls.from_dict(item))
                except ValueError:
                    continue
        return summaries


@dataclass(frozen=True)
class ExecutionSummary:
    """Typed representation of an execution status returned by the API."""

    id: str
    workflow_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ExecutionSummary":
        identifier = payload.get("id") or payload.get("execution_id")
        if not identifier:
            raise ValueError("execution payload is missing an 'id' field")
        return cls(
            id=str(identifier),
            workflow_id=payload.get("workflow_id"),
            status=payload.get("status"),
            created_at=payload.get("created_at") or payload.get("createdAt"),
            updated_at=payload.get("updated_at") or payload.get("updatedAt"),
            metadata=payload.get("metadata"),
        )

    @classmethod
    def parse_many(cls, payload: Any) -> List["ExecutionSummary"]:
        items: Iterable[Any]
        if isinstance(payload, dict):
            items = payload.get("executions") or payload.get("items") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        summaries: List[ExecutionSummary] = []
        for item in items:
            if isinstance(item, dict):
                try:
                    summaries.append(cls.from_dict(item))
                except ValueError:
                    continue
        return summaries
