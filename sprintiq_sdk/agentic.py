from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence, Union

from .client import SprintIQClient

__all__ = ["ContextClient", "MCPClient", "TeamDelegationClient"]


class ContextClient:
    """Helper utilities for working with organizational context entries."""

    def __init__(self, client: SprintIQClient) -> None:
        self._client = client

    def list(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        tag: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: Optional[bool] = None,
    ) -> Any:
        return self._client.list_context_entries(
            page=page,
            limit=limit,
            tag=tag,
            priority=priority,
            search=search,
            include_inactive=include_inactive,
        )

    def create(
        self,
        *,
        title: str,
        content: str,
        description: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        priority: Optional[str] = None,
    ) -> Any:
        return self._client.create_context_entry(
            title=title,
            content=content,
            description=description,
            entry_type=entry_type,
            tags=tags,
            priority=priority,
        )

    def get(self, context_id: str) -> Any:
        return self._client.get_context_entry(context_id)

    def update(
        self,
        context_id: str,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        priority: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Any:
        return self._client.update_context_entry(
            context_id,
            title=title,
            content=content,
            description=description,
            entry_type=entry_type,
            tags=tags,
            priority=priority,
            is_active=is_active,
        )

    def delete(self, context_id: str) -> Any:
        return self._client.delete_context_entry(context_id)


class MCPClient:
    """Client helper for MCP server administration."""

    def __init__(self, client: SprintIQClient) -> None:
        self._client = client

    def list_servers(self) -> Any:
        return self._client.list_mcp_servers()

    def create_server(
        self,
        *,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Any:
        return self._client.create_mcp_server(
            name=name,
            base_url=base_url,
            api_key=api_key,
            enabled=enabled,
        )

    def update_server(
        self,
        server_id: str,
        *,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Any:
        return self._client.update_mcp_server(
            server_id,
            name=name,
            base_url=base_url,
            api_key=api_key,
            enabled=enabled,
        )

    def delete_server(self, server_id: str) -> Any:
        return self._client.delete_mcp_server(server_id)

    def check_health(self, server_id: str) -> Any:
        return self._client.get_mcp_server_health(server_id)


class TeamDelegationClient:
    """Agentic task routing helper over the team delegation API surface."""

    def __init__(self, client: SprintIQClient, *, team_id: Optional[str] = None) -> None:
        self._client = client
        self._team_id = team_id

    def with_team(self, team_id: Optional[str]) -> "TeamDelegationClient":
        return TeamDelegationClient(self._client, team_id=team_id)

    def list_tasks(
        self,
        *,
        team_id: Optional[str] = None,
        status: Optional[Union[str, Sequence[str]]] = None,
        assignee_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        filters_team = team_id or self._team_id
        return self._client.list_delegation_tasks(
            team_id=filters_team,
            status=status,
            assignee_id=assignee_id,
            limit=limit,
        )

    def create_task(
        self,
        *,
        team_id: Optional[str] = None,
        title: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        complexity: Optional[str] = None,
        due_at: Optional[str] = None,
        created_by: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Iterable[str]] = None,
        skill_requirements: Optional[Iterable[str]] = None,
        estimated_hours: Optional[float] = None,
        actual_hours: Optional[float] = None,
        execution_id: Optional[str] = None,
        assignee_ids: Optional[Iterable[str]] = None,
        auto_assign: Optional[Dict[str, Any]] = None,
        delegated_by: Optional[str] = None,
        workload: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Any:
        target_team = team_id or self._team_id
        if not target_team:
            raise ValueError("team_id is required")
        return self._client.create_delegation_task(
            team_id=target_team,
            title=title,
            description=description,
            priority=priority,
            status=status,
            complexity=complexity,
            due_at=due_at,
            created_by=created_by,
            context=context,
            tags=tags,
            skill_requirements=skill_requirements,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            execution_id=execution_id,
            assignee_ids=assignee_ids,
            auto_assign=auto_assign,
            delegated_by=delegated_by,
            workload=workload,
            notes=notes,
        )

    def get_task(self, task_id: str) -> Any:
        return self._client.get_delegation_task(task_id)

    def update_task_status(
        self,
        task_id: str,
        *,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Any:
        return self._client.update_delegation_task_status(
            task_id,
            status=status,
            payload=payload,
            reason=reason,
        )

    def update_assignment_status(
        self,
        assignment_id: str,
        *,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Any:
        return self._client.update_delegation_assignment_status(
            assignment_id,
            status=status,
            payload=payload,
            reason=reason,
        )

    def add_task_update(
        self,
        task_id: str,
        *,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        member_id: Optional[str] = None,
    ) -> Any:
        return self._client.add_delegation_task_update(
            task_id,
            event_type=event_type,
            payload=payload,
            member_id=member_id,
        )

    def bulk_update_status(
        self,
        *,
        task_ids: Sequence[str],
        status: str,
        reason: Optional[str] = None,
        member_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._client.bulk_update_delegation_task_status(
            task_ids=task_ids,
            status=status,
            reason=reason,
            member_id=member_id,
            metadata=metadata,
        )

    def bulk_assign(
        self,
        *,
        task_ids: Sequence[str],
        assignee_ids: Sequence[str],
        status: Optional[str] = None,
        replace_existing: Optional[bool] = None,
        delegated_by: Optional[str] = None,
        workload: Optional[float] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._client.bulk_assign_delegation_tasks(
            task_ids=task_ids,
            assignee_ids=assignee_ids,
            status=status,
            replace_existing=replace_existing,
            delegated_by=delegated_by,
            workload=workload,
            notes=notes,
            metadata=metadata,
        )

    def export_tasks(
        self,
        *,
        team_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        include_updates: Optional[bool] = None,
        format: str = "json",
    ) -> Any:
        target_team = team_id or self._team_id
        return self._client.export_delegation_tasks(
            team_id=target_team,
            status=status,
            limit=limit,
            include_updates=include_updates,
            format=format,
        )

