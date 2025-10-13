from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from .client import PlexityClient

__all__ = ["InsightClient"]


class InsightClient:
    """Convenience wrapper for orchestrator insight jobs."""

    def __init__(self, client: PlexityClient) -> None:
        self._client = client

    def list_jobs(
        self,
        *,
        status: Optional[Iterable[str]] = None,
        job_type: Optional[str] = None,
        team_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        return self._client.list_insight_jobs(
            status=status,
            job_type=job_type,
            team_id=team_id,
            limit=limit,
        )

    def get_latest(
        self,
        *,
        job_type: Optional[str] = None,
    ) -> Any:
        return self._client.get_latest_insight_job(job_type=job_type)

    def create_job(
        self,
        *,
        job_type: str,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        team_id: Optional[str] = None,
        priority: Optional[int] = None,
        delay_ms: Optional[int] = None,
    ) -> Any:
        return self._client.create_insight_job(
            job_type=job_type,
            payload=payload,
            metadata=metadata,
            team_id=team_id,
            priority=priority,
            delay_ms=delay_ms,
        )

    def get_job(self, job_id: str) -> Any:
        return self._client.get_insight_job(job_id)

    def get_result(self, job_id: str) -> Any:
        return self._client.get_insight_job_result(job_id)
