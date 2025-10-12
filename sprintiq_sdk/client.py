from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import requests


class SprintIQError(Exception):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, message: str, payload: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class SprintIQClient:
    """Lightweight HTTP client for the SprintIQ orchestrator API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self.timeout = timeout
        self._session = session or requests.Session()
        self.default_headers: Dict[str, str] = dict(default_headers or {})

    def set_api_key(self, api_key: Optional[str]) -> None:
        self.api_key = api_key

    def set_token(self, token: Optional[str]) -> None:
        self.token = token

    def set_default_header(self, name: str, value: Optional[str]) -> None:
        if value is None:
            self.default_headers.pop(name, None)
        else:
            self.default_headers[name] = value

    # Workflows -----------------------------------------------------------------
    def list_workflows(self) -> Any:
        return self._request("GET", "/workflows")

    def get_workflow(self, workflow_id: str) -> Any:
        return self._request("GET", f"/workflows/{self._encode(workflow_id)}")

    def save_workflow(self, spec: Dict[str, Any]) -> Any:
        workflow_id = spec.get("id")
        if not workflow_id:
            raise ValueError("spec.id is required")
        payload = {"id": workflow_id, "spec": spec}
        return self._request("POST", "/workflows", json_payload=payload)

    def delete_workflow(self, workflow_id: str) -> Any:
        return self._request("DELETE", f"/workflows/{self._encode(workflow_id)}")

    # Team integrations -------------------------------------------------------
    def get_team_integration_meta(self) -> Any:
        return self._request("GET", "/team-delegation/integrations/meta")

    def list_team_integration_apps(self, *, team_id: Optional[str] = None) -> Any:
        params: Dict[str, str] = {}
        if team_id:
            params["team_id"] = team_id
        resp = self._request("GET", "/team-delegation/integrations/apps", params=params or None)
        return resp.get("apps", []) if isinstance(resp, dict) else resp

    def create_team_integration_app(self, payload: Dict[str, Any]) -> Any:
        resp = self._request("POST", "/team-delegation/integrations/apps", json_payload=payload)
        return resp.get("app") if isinstance(resp, dict) else resp

    def update_team_integration_app(self, app_id: str, payload: Dict[str, Any]) -> Any:
        resp = self._request(
            "PATCH",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}",
            json_payload=payload,
        )
        return resp.get("app") if isinstance(resp, dict) else resp

    def delete_team_integration_app(self, app_id: str) -> None:
        self._request("DELETE", f"/team-delegation/integrations/apps/{self._encode(app_id)}")

    def list_team_integration_webhooks(self, app_id: str) -> Any:
        resp = self._request(
            "GET",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}/webhooks",
        )
        return resp.get("webhooks", []) if isinstance(resp, dict) else resp

    def register_team_integration_webhook(self, app_id: str, payload: Dict[str, Any]) -> Any:
        resp = self._request(
            "POST",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}/webhooks",
            json_payload=payload,
        )
        return resp.get("webhook") if isinstance(resp, dict) else resp

    def update_team_integration_webhook(self, webhook_id: str, payload: Dict[str, Any]) -> Any:
        resp = self._request(
            "PATCH",
            f"/team-delegation/integrations/webhooks/{self._encode(webhook_id)}",
            json_payload=payload,
        )
        return resp.get("webhook") if isinstance(resp, dict) else resp

    def delete_team_integration_webhook(self, webhook_id: str) -> None:
        self._request("DELETE", f"/team-delegation/integrations/webhooks/{self._encode(webhook_id)}")

    def list_team_integration_plugins(self, app_id: str) -> Any:
        resp = self._request(
            "GET",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}/plugins",
        )
        return resp.get("plugins", []) if isinstance(resp, dict) else resp

    def register_team_integration_plugin(self, app_id: str, payload: Dict[str, Any]) -> Any:
        resp = self._request(
            "POST",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}/plugins",
            json_payload=payload,
        )
        return resp.get("plugin") if isinstance(resp, dict) else resp

    def update_team_integration_plugin(self, plugin_id: str, payload: Dict[str, Any]) -> Any:
        resp = self._request(
            "PATCH",
            f"/team-delegation/integrations/plugins/{self._encode(plugin_id)}",
            json_payload=payload,
        )
        return resp.get("plugin") if isinstance(resp, dict) else resp

    def delete_team_integration_plugin(self, plugin_id: str) -> None:
        self._request("DELETE", f"/team-delegation/integrations/plugins/{self._encode(plugin_id)}")

    def list_team_integration_events(self, *, team_id: Optional[str] = None, limit: Optional[int] = None) -> Any:
        params: Dict[str, str] = {}
        if team_id:
            params["team_id"] = team_id
        if limit is not None:
            params["limit"] = str(limit)
        resp = self._request("GET", "/team-delegation/integrations/events", params=params or None)
        return resp.get("events", []) if isinstance(resp, dict) else resp

    def emit_team_integration_test(self, app_id: str, payload: Dict[str, Any]) -> Any:
        return self._request(
            "POST",
            f"/team-delegation/integrations/apps/{self._encode(app_id)}/test",
            json_payload=payload,
        )

    # GraphRAG telemetry -----------------------------------------------------

    def record_graphrag_entity_events(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/entity", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_relationship_events(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/relationship", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_community_events(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/community", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_query_coverage(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/query", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_indexing_operations(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/indexing", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_schema_snapshots(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/schema", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    def record_graphrag_topology_snapshots(self, events: Any) -> int:
        payload = self._wrap_events(events)
        res = self._request("POST", "/graphrag/ingest/topology", json_payload=payload)
        return int(res.get("accepted", len(payload["events"]))) if isinstance(res, dict) else len(payload["events"])

    # Insight jobs -----------------------------------------------------------------
    def list_insight_jobs(
        self,
        *,
        status: Optional[Iterable[str]] = None,
        job_type: Optional[str] = None,
        team_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if status:
            values = [str(item).strip() for item in status if str(item).strip()]
            if values:
                params["status"] = ",".join(values)
        if job_type:
            params["job_type"] = job_type
        if team_id:
            params["team_id"] = team_id
        if limit is not None:
            params["limit"] = str(int(limit))
        resp = self._request("GET", "/insights/jobs", params=params or None)
        return resp.get("jobs", []) if isinstance(resp, dict) else resp

    def get_latest_insight_job(self, *, job_type: Optional[str] = None) -> Any:
        params: Dict[str, str] = {}
        if job_type:
            params["job_type"] = job_type
        resp = self._request("GET", "/insights/jobs/latest", params=params or None)
        return resp.get("job") if isinstance(resp, dict) else resp

    def create_insight_job(
        self,
        *,
        job_type: str,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        team_id: Optional[str] = None,
        priority: Optional[int] = None,
        delay_ms: Optional[int] = None,
    ) -> Any:
        job_value = (job_type or "").strip()
        if not job_value:
            raise ValueError("job_type is required")
        body: Dict[str, Any] = {
            "job_type": job_value,
            "payload": dict(payload or {}),
        }
        if metadata is not None:
            body["metadata"] = dict(metadata)
        if team_id is not None:
            body["team_id"] = team_id
        if priority is not None:
            body["priority"] = int(priority)
        if delay_ms is not None:
            body["delay_ms"] = int(delay_ms)
        resp = self._request("POST", "/insights/jobs", json_payload=body)
        return resp.get("job") if isinstance(resp, dict) else resp

    def get_insight_job(self, job_id: str) -> Any:
        identifier = (job_id or "").strip()
        if not identifier:
            raise ValueError("job_id is required")
        resp = self._request("GET", f"/insights/jobs/{self._encode(identifier)}")
        return resp.get("job") if isinstance(resp, dict) else resp

    def get_insight_job_result(self, job_id: str) -> Any:
        identifier = (job_id or "").strip()
        if not identifier:
            raise ValueError("job_id is required")
        resp = self._request("GET", f"/insights/jobs/{self._encode(identifier)}/result")
        if isinstance(resp, dict):
            return resp.get("result")
        return resp

    # Context memory & MCP ------------------------------------------------------

    def list_context_entries(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        tag: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: Optional[bool] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if page is not None:
            params["page"] = str(int(page))
        if limit is not None:
            params["limit"] = str(int(limit))
        if tag:
            params["tag"] = tag
        if priority:
            params["priority"] = priority
        if search:
            params["search"] = search
        if include_inactive is not None:
            params["include_inactive"] = self._bool_to_str(include_inactive)
        return self._request("GET", "/context", params=params or None)

    def create_context_entry(
        self,
        *,
        title: str,
        content: str,
        description: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        priority: Optional[str] = None,
    ) -> Any:
        body: Dict[str, Any] = {
            "title": (title or "").strip(),
            "content": (content or "").strip(),
        }
        if not body["title"]:
            raise ValueError("title is required")
        if not body["content"]:
            raise ValueError("content is required")
        if description is not None:
            body["description"] = description
        if entry_type:
            body["type"] = entry_type
        if tags is not None:
            body["tags"] = [str(tag) for tag in tags]
        if priority:
            body["priority"] = priority
        return self._request("POST", "/context", json_payload=body)

    def get_context_entry(self, context_id: str) -> Any:
        return self._request("GET", f"/context/{self._encode(context_id)}")

    def update_context_entry(
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
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if description is not None:
            payload["description"] = description
        if entry_type is not None:
            payload["type"] = entry_type
        if tags is not None:
            payload["tags"] = [str(tag) for tag in tags]
        if priority is not None:
            payload["priority"] = priority
        if is_active is not None:
            payload["isActive"] = bool(is_active)
        if not payload:
            raise ValueError("at least one field must be provided for update")
        return self._request("PUT", f"/context/{self._encode(context_id)}", json_payload=payload)

    def delete_context_entry(self, context_id: str) -> Any:
        return self._request("DELETE", f"/context/{self._encode(context_id)}")

    def list_mcp_servers(self) -> Any:
        return self._request("GET", "/mcp/servers")

    def create_mcp_server(
        self,
        *,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Any:
        payload: Dict[str, Any] = {
            "name": (name or "").strip(),
            "base_url": (base_url or "").strip(),
        }
        if not payload["name"]:
            raise ValueError("name is required")
        if not payload["base_url"]:
            raise ValueError("base_url is required")
        if api_key is not None:
            payload["api_key"] = api_key
        if enabled is not None:
            payload["enabled"] = bool(enabled)
        return self._request("POST", "/mcp/servers", json_payload=payload)

    def update_mcp_server(
        self,
        server_id: str,
        *,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Any:
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if base_url is not None:
            payload["base_url"] = base_url
        if api_key is not None:
            payload["api_key"] = api_key
        if enabled is not None:
            payload["enabled"] = bool(enabled)
        if not payload:
            raise ValueError("at least one field must be provided for update")
        return self._request("PUT", f"/mcp/servers/{self._encode(server_id)}", json_payload=payload)

    def delete_mcp_server(self, server_id: str) -> Any:
        return self._request("DELETE", f"/mcp/servers/{self._encode(server_id)}")

    def get_mcp_server_health(self, server_id: str) -> Any:
        return self._request("GET", f"/mcp/servers/{self._encode(server_id)}/health")

    # Team delegation & task orchestration --------------------------------------

    def list_delegation_tasks(
        self,
        *,
        team_id: Optional[str] = None,
        status: Optional[Union[str, Sequence[str]]] = None,
        assignee_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if team_id:
            params["team_id"] = team_id
        if status:
            if isinstance(status, str):
                params["status"] = status
            else:
                params["status"] = ",".join(str(value) for value in status)
        if assignee_id:
            params["assignee_id"] = assignee_id
        if limit is not None:
            params["limit"] = str(int(limit))
        return self._request("GET", "/team-delegation/tasks", params=params or None)

    def create_delegation_task(
        self,
        *,
        team_id: str,
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
        team_value = (team_id or "").strip()
        if not team_value:
            raise ValueError("team_id is required")
        title_value = (title or "").strip()
        if not title_value:
            raise ValueError("title is required")
        payload: Dict[str, Any] = {
            "team_id": team_value,
            "title": title_value,
        }
        if description is not None:
            payload["description"] = description
        if priority is not None:
            payload["priority"] = priority
        if status is not None:
            payload["status"] = status
        if complexity is not None:
            payload["complexity"] = complexity
        if due_at is not None:
            payload["due_at"] = due_at
        if created_by is not None:
            payload["created_by"] = created_by
        if context is not None:
            payload["context"] = context
        if tags is not None:
            payload["tags"] = [str(tag) for tag in tags]
        if skill_requirements is not None:
            payload["skill_requirements"] = [str(skill) for skill in skill_requirements]
        if estimated_hours is not None:
            payload["estimated_hours"] = float(estimated_hours)
        if actual_hours is not None:
            payload["actual_hours"] = float(actual_hours)
        if execution_id is not None:
            payload["execution_id"] = execution_id
        if assignee_ids is not None:
            payload["assignee_ids"] = [str(assignee) for assignee in assignee_ids]
        if auto_assign is not None:
            payload["auto_assign"] = dict(auto_assign)
        if delegated_by is not None:
            payload["delegated_by"] = delegated_by
        if workload is not None:
            payload["workload"] = float(workload)
        if notes is not None:
            payload["notes"] = notes
        return self._request("POST", "/team-delegation/tasks", json_payload=payload)

    def get_delegation_task(self, task_id: str) -> Any:
        return self._request("GET", f"/team-delegation/tasks/{self._encode(task_id)}")

    def update_delegation_task_status(
        self,
        task_id: str,
        *,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Any:
        status_value = (status or "").strip().lower()
        if not status_value:
            raise ValueError("status is required")
        body: Dict[str, Any] = {"status": status_value}
        if payload is not None:
            body["payload"] = payload
        if reason is not None:
            body["reason"] = reason
        return self._request(
            "POST",
            f"/team-delegation/tasks/{self._encode(task_id)}/status",
            json_payload=body,
        )

    def update_delegation_assignment_status(
        self,
        assignment_id: str,
        *,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Any:
        status_value = (status or "").strip().lower()
        if not status_value:
            raise ValueError("status is required")
        body: Dict[str, Any] = {"status": status_value}
        if payload is not None:
            body["payload"] = payload
        if reason is not None:
            body["reason"] = reason
        return self._request(
            "POST",
            f"/team-delegation/assignments/{self._encode(assignment_id)}/status",
            json_payload=body,
        )

    def add_delegation_task_update(
        self,
        task_id: str,
        *,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        member_id: Optional[str] = None,
    ) -> Any:
        event_value = (event_type or "").strip()
        if not event_value:
            raise ValueError("event_type is required")
        body: Dict[str, Any] = {
            "event_type": event_value,
        }
        if payload is not None:
            body["payload"] = payload
        if member_id is not None:
            body["member_id"] = member_id
        return self._request(
            "POST",
            f"/team-delegation/tasks/{self._encode(task_id)}/updates",
            json_payload=body,
        )

    def bulk_update_delegation_task_status(
        self,
        *,
        task_ids: Sequence[str],
        status: str,
        reason: Optional[str] = None,
        member_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        ids = [str(value) for value in task_ids if str(value)]
        if not ids:
            raise ValueError("task_ids is required")
        status_value = (status or "").strip().lower()
        if not status_value:
            raise ValueError("status is required")
        body: Dict[str, Any] = {
            "task_ids": ids,
            "status": status_value,
        }
        if reason is not None:
            body["reason"] = reason
        if member_id is not None:
            body["member_id"] = member_id
        if metadata is not None:
            body["metadata"] = metadata
        return self._request(
            "POST",
            "/team-delegation/tasks/bulk/status",
            json_payload=body,
        )

    def bulk_assign_delegation_tasks(
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
        task_values = [str(value) for value in task_ids if str(value)]
        if not task_values:
            raise ValueError("task_ids is required")
        assignee_values = [str(value) for value in assignee_ids if str(value)]
        if not assignee_values:
            raise ValueError("assignee_ids is required")
        body: Dict[str, Any] = {
            "task_ids": task_values,
            "assignee_ids": assignee_values,
        }
        if status is not None:
            body["status"] = status
        if replace_existing is not None:
            body["replace_existing"] = bool(replace_existing)
        if delegated_by is not None:
            body["delegated_by"] = delegated_by
        if workload is not None:
            body["workload"] = float(workload)
        if notes is not None:
            body["notes"] = notes
        if metadata is not None:
            body["metadata"] = metadata
        return self._request(
            "POST",
            "/team-delegation/tasks/bulk/assign",
            json_payload=body,
        )

    def export_delegation_tasks(
        self,
        *,
        team_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        include_updates: Optional[bool] = None,
        format: str = "json",
    ) -> Any:
        params: Dict[str, str] = {"format": format}
        if team_id:
            params["team_id"] = team_id
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = str(int(limit))
        if include_updates is not None:
            params["include_updates"] = self._bool_to_str(include_updates)
        return self._request(
            "GET",
            "/team-delegation/tasks/export",
            params=params,
        )

    # Integration automation ----------------------------------------------------
    def clone_repository(
        self,
        *,
        repository_url: str,
        shallow_clone: bool = True,
        refresh_analysis: Optional[bool] = None,
        auth_token: Optional[str] = None,
    ) -> Any:
        repo = (repository_url or "").strip()
        if not repo:
            raise ValueError("repository_url is required")
        payload: Dict[str, Any] = {"repository_url": repo}
        if not shallow_clone:
            payload["shallow_clone"] = False
        if refresh_analysis is not None:
            payload["refresh"] = bool(refresh_analysis)
        headers = {"authorization": f"Bearer {auth_token}"} if auth_token else None
        return self._request("POST", "/github/clone", json_payload=payload, headers=headers)

    def prepare_integration(
        self,
        *,
        repository_url: str,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
        backup_original: Optional[bool] = None,
        shallow_clone: bool = True,
        refresh_analysis: Optional[bool] = None,
        auth_token: Optional[str] = None,
    ) -> Any:
        repo = (repository_url or "").strip()
        if not repo:
            raise ValueError("repository_url is required")
        payload: Dict[str, Any] = {"repository_url": repo}
        if branch_name:
            payload["branch_name"] = branch_name
        if base_branch:
            payload["base_branch"] = base_branch
        if backup_original is not None:
            payload["backup_original"] = bool(backup_original)
        if not shallow_clone:
            payload["shallow_clone"] = False
        if refresh_analysis is not None:
            payload["refresh"] = bool(refresh_analysis)
        headers = {"authorization": f"Bearer {auth_token}"} if auth_token else None
        return self._request("POST", "/github/prepare-integration", json_payload=payload, headers=headers)

    def install_integration_dependencies(
        self,
        *,
        repository_path: str,
        dependencies: Optional[Iterable[str]] = None,
        dev_dependencies: Optional[Iterable[str]] = None,
        python_dependencies: Optional[Iterable[str]] = None,
    ) -> Any:
        path = (repository_path or "").strip()
        if not path:
            raise ValueError("repository_path is required")
        payload: Dict[str, Any] = {"repository_path": path}
        if dependencies:
            payload["dependencies"] = [str(dep) for dep in dependencies]
        if dev_dependencies:
            payload["dev_dependencies"] = [str(dep) for dep in dev_dependencies]
        if python_dependencies:
            payload["python_dependencies"] = [str(dep) for dep in python_dependencies]
        return self._request("POST", "/integration/install-dependencies", json_payload=payload)

    def write_integration_files(
        self,
        *,
        repository_path: str,
        files: Dict[str, Any],
        create_backup: Optional[bool] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        path = (repository_path or "").strip()
        if not path:
            raise ValueError("repository_path is required")
        if not files:
            raise ValueError("files is required")
        payload: Dict[str, Any] = {"repository_path": path, "files": files}
        if create_backup is not None:
            payload["create_backup"] = bool(create_backup)
        if config is not None:
            payload["config"] = config
        return self._request("POST", "/integration/write-files", json_payload=payload)

    def run_integration_tests(self, *, repository_path: str) -> Any:
        path = (repository_path or "").strip()
        if not path:
            raise ValueError("repository_path is required")
        payload = {"repository_path": path}
        return self._request("POST", "/integration/test", json_payload=payload)

    def create_github_pull_request(
        self,
        *,
        repository_url: str,
        repository_path: Optional[str] = None,
        branch_name: str,
        base_branch: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Any:
        repo = (repository_url or "").strip()
        if not repo:
            raise ValueError("repository_url is required")
        branch = (branch_name or "").strip()
        if not branch:
            raise ValueError("branch_name is required")
        payload: Dict[str, Any] = {
            "repository_url": repo,
            "branch_name": branch,
        }
        if repository_path:
            payload["repository_path"] = repository_path
        if base_branch:
            payload["base_branch"] = base_branch
        if title:
            payload["title"] = title
        if body:
            payload["description"] = body
        headers = {"authorization": f"Bearer {auth_token}"} if auth_token else None
        return self._request("POST", "/github/create-pr", json_payload=payload, headers=headers)

    # Claude integration support -------------------------------------------------
    def create_claude_integration_plan(
        self,
        *,
        repository: Optional[Dict[str, Any]] = None,
        recommendations: Optional[str] = None,
        workflow: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload: Dict[str, Any] = {}
        if repository is not None:
            payload["repository"] = repository
        if recommendations is not None:
            payload["recommendations"] = recommendations
        if workflow is not None:
            payload["workflow"] = workflow
        if confidence_score is not None:
            payload["confidence_score"] = float(confidence_score)
        if metadata is not None:
            payload["metadata"] = metadata
        return self._request("POST", "/claude/integration-plans", json_payload=payload)

    def list_claude_integration_plans(self, *, limit: Optional[int] = None) -> Any:
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(int(limit))
        return self._request("GET", "/claude/integration-plans", params=params or None)

    def list_claude_sessions(
        self,
        *,
        limit: Optional[int] = None,
        status: Optional[Iterable[str]] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(int(limit))
        if status:
            params["status"] = ",".join(str(value) for value in status if str(value))
        return self._request("GET", "/claude-agent/sessions", params=params or None)

    def create_claude_session(
        self,
        *,
        repository_name: str,
        team_id: Optional[str] = None,
        repository_owner: Optional[str] = None,
        repository_url: Optional[str] = None,
        default_branch: Optional[str] = None,
        tasks: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> Any:
        name = (repository_name or "").strip()
        if not name:
            raise ValueError("repository_name is required")
        payload: Dict[str, Any] = {"repository_name": name}
        if team_id is not None:
            payload["team_id"] = team_id
        if repository_owner is not None:
            payload["repository_owner"] = repository_owner
        if repository_url is not None:
            payload["repository_url"] = repository_url
        if default_branch is not None:
            payload["default_branch"] = default_branch
        if tasks is not None:
            payload["tasks"] = [dict(task) for task in tasks]
        return self._request("POST", "/claude-agent/sessions", json_payload=payload)

    def get_claude_session(self, session_id: str) -> Any:
        session = (session_id or "").strip()
        if not session:
            raise ValueError("session_id is required")
        return self._request("GET", f"/claude-agent/sessions/{self._encode(session)}")

    def log_claude_session(
        self,
        session_id: str,
        *,
        message: str,
        level: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Any:
        session = (session_id or "").strip()
        if not session:
            raise ValueError("session_id is required")
        text = (message or "").strip()
        if not text:
            raise ValueError("message is required")
        payload: Dict[str, Any] = {"message": text}
        if level is not None:
            payload["level"] = level
        if details is not None:
            payload["details"] = details
        return self._request(
            "POST",
            f"/claude-agent/sessions/{self._encode(session)}/logs",
            json_payload=payload,
        )

    def update_claude_task(
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
        session = (session_id or "").strip()
        task = (task_id or "").strip()
        if not session or not task:
            raise ValueError("session_id and task_id are required")
        payload: Dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if progress is not None:
            payload["progress"] = float(progress)
        if started_at is not None:
            payload["started_at"] = started_at
        if completed_at is not None:
            payload["completed_at"] = completed_at
        if metadata is not None:
            payload["metadata"] = metadata
        if not payload:
            raise ValueError("at least one field must be provided for update")
        return self._request(
            "PATCH",
            f"/claude-agent/sessions/{self._encode(session)}/tasks/{self._encode(task)}",
            json_payload=payload,
        )

    def rerun_claude_session(self, session_id: str) -> Any:
        session = (session_id or "").strip()
        if not session:
            raise ValueError("session_id is required")
        return self._request(
            "POST",
            f"/claude-agent/sessions/{self._encode(session)}/rerun",
            json_payload={},
        )

    # GraphRAG operations -------------------------------------------------------
    def search_graphrag(
        self,
        query: str,
        *,
        search_type: Optional[str] = None,
        max_tokens: Optional[int] = None,
        max_communities: Optional[int] = None,
        max_entities: Optional[int] = None,
        evaluate: Optional[bool] = None,
        disable_evaluation: Optional[bool] = None,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        engine: Optional[str] = None,
        use_microsoft_cli: Optional[bool] = None,
        microsoft_cli: Optional[Dict[str, Any]] = None,
    ) -> Any:
        text = (query or "").strip()
        if not text:
            raise ValueError("query is required")

        payload: Dict[str, Any] = {"query": text}
        if search_type:
            normalized = search_type.lower()
            if normalized not in {"local", "global", "hybrid"}:
                raise ValueError("search_type must be one of 'local', 'global', or 'hybrid'")
            payload["search_type"] = normalized
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if max_communities is not None:
            payload["max_communities"] = int(max_communities)
        if max_entities is not None:
            payload["max_entities"] = int(max_entities)
        if evaluate is not None:
            payload["evaluate"] = bool(evaluate)
        if disable_evaluation is not None:
            payload["disable_evaluation"] = bool(disable_evaluation)

        self._apply_graphrag_context(payload, org_id, team_id, environment)

        overrides = self._build_graphrag_config_overrides(
            config_overrides,
            engine=engine,
            use_microsoft_cli=use_microsoft_cli,
            microsoft_cli=microsoft_cli,
        )
        if overrides:
            payload["config_overrides"] = overrides

        return self._request("POST", "/graphrag/search", json_payload=payload)

    def index_graphrag(
        self,
        documents: Iterable[Dict[str, Any]],
        *,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
        mode: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None,
        llm_model: Optional[str] = None,
        detect_changes: Optional[bool] = None,
        detect_deletions: Optional[bool] = None,
        invalidate_stale: Optional[bool] = None,
        force_reindex: Optional[bool] = None,
        skip_unchanged: Optional[bool] = None,
        schema_version: Optional[str] = None,
        document_ids: Optional[Iterable[str]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload = self._prepare_graphrag_index_payload(
            documents,
            org_id=org_id,
            team_id=team_id,
            environment=environment,
            mode=mode,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model,
            llm_model=llm_model,
            detect_changes=detect_changes,
            detect_deletions=detect_deletions,
            invalidate_stale=invalidate_stale,
            force_reindex=force_reindex,
            skip_unchanged=skip_unchanged,
            schema_version=schema_version,
            document_ids=document_ids,
            config_overrides=config_overrides,
        )
        return self._request("POST", "/graphrag/index", json_payload=payload)

    def incremental_index_graphrag(
        self,
        documents: Iterable[Dict[str, Any]],
        *,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
        mode: Optional[str] = "incremental",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None,
        llm_model: Optional[str] = None,
        detect_changes: Optional[bool] = None,
        detect_deletions: Optional[bool] = None,
        invalidate_stale: Optional[bool] = None,
        force_reindex: Optional[bool] = None,
        skip_unchanged: Optional[bool] = None,
        schema_version: Optional[str] = None,
        document_ids: Optional[Iterable[str]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload = self._prepare_graphrag_index_payload(
            documents,
            org_id=org_id,
            team_id=team_id,
            environment=environment,
            mode=mode or "incremental",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model,
            llm_model=llm_model,
            detect_changes=detect_changes,
            detect_deletions=detect_deletions,
            invalidate_stale=invalidate_stale,
            force_reindex=force_reindex,
            skip_unchanged=skip_unchanged,
            schema_version=schema_version,
            document_ids=document_ids,
            config_overrides=config_overrides,
        )
        return self._request("POST", "/graphrag/incremental-index", json_payload=payload)

    def get_graphrag_stats(
        self,
        *,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> Any:
        params = self._graphrag_context_query(org_id, team_id, environment)
        return self._request("GET", "/graphrag/stats", params=params)

    def get_graphrag_entities(
        self,
        *,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        include_neighbors: Optional[bool] = None,
        max_hops: Optional[int] = None,
        entity_types: Optional[Iterable[str]] = None,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> Any:
        params = self._graphrag_context_query(org_id, team_id, environment)
        if query:
            params["query"] = query
        if limit is not None:
            params["limit"] = str(int(limit))
        if include_neighbors is not None:
            params["include_neighbors"] = self._bool_to_str(include_neighbors)
        if max_hops is not None:
            params["max_hops"] = str(int(max_hops))
        if entity_types:
            values = [str(value) for value in entity_types]
            if values:
                params["entity_types"] = ",".join(values) if len(values) > 1 else values[0]
        return self._request("GET", "/graphrag/entities", params=params)

    def get_graphrag_communities(
        self,
        *,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        level: Optional[int] = None,
        org_id: Optional[str] = None,
        team_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> Any:
        params = self._graphrag_context_query(org_id, team_id, environment)
        if query:
            params["query"] = query
        if limit is not None:
            params["limit"] = str(int(limit))
        if min_size is not None:
            params["min_size"] = str(int(min_size))
        if max_size is not None:
            params["max_size"] = str(int(max_size))
        if level is not None:
            params["level"] = str(int(level))
        return self._request("GET", "/graphrag/communities", params=params)

    # Executions ----------------------------------------------------------------
    def list_executions(
        self,
        *,
        status: Optional[Iterable[str]] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if status:
            params["status"] = ",".join(status)
        if limit is not None:
            params["limit"] = str(limit)
        if since:
            params["from"] = since
        if until:
            params["to"] = until
        if before:
            params["before"] = before
        return self._request("GET", "/executions", params=params)

    def get_execution(self, execution_id: str) -> Any:
        return self._request("GET", f"/executions/{self._encode(execution_id)}")

    def list_execution_steps(self, execution_id: str, *, limit: Optional[int] = None, after_id: Optional[str] = None) -> Any:
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if after_id:
            params["after_id"] = after_id
        return self._request("GET", f"/executions/{self._encode(execution_id)}/steps", params=params)

    def start_execution(self, *, workflow_id: str, input: Any | None = None, kind: Optional[str] = None) -> Any:
        payload: Dict[str, Any] = {"workflow_id": workflow_id}
        if input is not None:
            payload["input"] = input
        if kind:
            payload["kind"] = kind
        return self._request("POST", "/executions", json_payload=payload)

    def cancel_execution(self, execution_id: str) -> Any:
        return self._request("POST", f"/executions/{self._encode(execution_id)}/cancel")

    def resume_step(self, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("POST", f"/resume/{self._encode(token)}", json_payload=payload or {})

    def list_events(self, execution_id: str) -> Any:
        return self._request("GET", f"/events/{self._encode(execution_id)}")

    # Triggers ------------------------------------------------------------------
    def list_triggers(self) -> Any:
        return self._request("GET", "/triggers")

    # Internal helpers ----------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
        json_payload: Any | None = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = self._build_url(path)
        req_headers: Dict[str, str] = dict(self.default_headers)
        if headers:
            req_headers.update(headers)
        if self.api_key:
            req_headers["x-api-key"] = self.api_key
        if self.token:
            req_headers["authorization"] = f"Bearer {self.token}"

        response = self._session.request(
            method,
            url,
            params=params,
            json=json_payload,
            headers=req_headers,
            timeout=self.timeout,
        )
        if not response.ok:
            payload: Any
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            message = self._error_message(response.status_code, payload)
            raise SprintIQError(response.status_code, message, payload)

        if response.status_code == 204:
            return None

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        if not response.text:
            return None
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return response.text

    def _prepare_graphrag_index_payload(
        self,
        documents: Iterable[Dict[str, Any]],
        *,
        org_id: Optional[str],
        team_id: Optional[str],
        environment: Optional[str],
        mode: Optional[str],
        chunk_size: Optional[int],
        chunk_overlap: Optional[int],
        embedding_model: Optional[str],
        llm_model: Optional[str],
        detect_changes: Optional[bool],
        detect_deletions: Optional[bool],
        invalidate_stale: Optional[bool],
        force_reindex: Optional[bool],
        skip_unchanged: Optional[bool],
        schema_version: Optional[str],
        document_ids: Optional[Iterable[str]],
        config_overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        doc_list: List[Dict[str, Any]] = [dict(item) for item in documents]
        if not doc_list and not document_ids:
            raise ValueError("documents or document_ids are required")

        payload: Dict[str, Any] = {}
        if doc_list:
            payload["documents"] = doc_list

        self._apply_graphrag_context(payload, org_id, team_id, environment)

        if mode:
            payload["mode"] = mode
        if chunk_size is not None:
            payload["chunk_size"] = int(chunk_size)
        if chunk_overlap is not None:
            payload["chunk_overlap"] = int(chunk_overlap)
        if embedding_model:
            payload["embedding_model"] = embedding_model
        if llm_model:
            payload["llm_model"] = llm_model
        if detect_changes is not None:
            payload["detect_changes"] = bool(detect_changes)
        if detect_deletions is not None:
            payload["detect_deletions"] = bool(detect_deletions)
        if invalidate_stale is not None:
            payload["invalidate_stale"] = bool(invalidate_stale)
        if force_reindex is not None:
            payload["force_reindex"] = bool(force_reindex)
        if skip_unchanged is not None:
            payload["skip_unchanged"] = bool(skip_unchanged)
        if schema_version:
            payload["schema_version"] = schema_version
        if document_ids is not None:
            payload["document_ids"] = [str(value) for value in document_ids]

        overrides = self._build_graphrag_config_overrides(
            config_overrides,
            engine=None,
            use_microsoft_cli=None,
            microsoft_cli=None,
        )
        if overrides:
            payload["config_overrides"] = overrides

        return payload

    def _build_graphrag_config_overrides(
        self,
        config_overrides: Optional[Dict[str, Any]],
        *,
        engine: Optional[str],
        use_microsoft_cli: Optional[bool],
        microsoft_cli: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        overrides: Dict[str, Any] = dict(config_overrides or {})
        engine_setting: Optional[str]
        if engine:
            engine_setting = engine
        elif use_microsoft_cli is True:
            engine_setting = "microsoft"
        elif use_microsoft_cli is False:
            engine_setting = "native"
        else:
            engine_setting = None

        if engine_setting:
            overrides["engine"] = engine_setting

        if microsoft_cli:
            existing = overrides.get("microsoft")
            merged = dict(existing) if isinstance(existing, dict) else {}
            merged.update(microsoft_cli)
            overrides["microsoft"] = merged

        return overrides or None

    @staticmethod
    def _apply_graphrag_context(
        payload: Dict[str, Any],
        org_id: Optional[str],
        team_id: Optional[str],
        environment: Optional[str],
    ) -> None:
        if org_id:
            payload["org_id"] = org_id
        if team_id is not None:
            payload["team_id"] = team_id
        if environment:
            payload["environment"] = environment

    @staticmethod
    def _graphrag_context_query(
        org_id: Optional[str],
        team_id: Optional[str],
        environment: Optional[str],
    ) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if org_id:
            params["org_id"] = org_id
        if team_id is not None:
            params["team_id"] = str(team_id)
        if environment:
            params["environment"] = environment
        return params

    @staticmethod
    def _bool_to_str(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _wrap_events(events: Any) -> Dict[str, Any]:
        if isinstance(events, dict):
            return {"events": [events]}
        if isinstance(events, list):
            return {"events": events}
        if hasattr(events, "__iter__"):
            materialised = list(events)
            return {"events": materialised}
        raise ValueError("events must be iterable dictionaries or a single dictionary")

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    @staticmethod
    def _encode(value: str) -> str:
        from urllib.parse import quote

        return quote(value, safe="")

    @staticmethod
    def _error_message(status_code: int, payload: Any) -> str:
        if isinstance(payload, dict) and payload.get("error"):
            return str(payload["error"])
        if status_code == 401:
            return "unauthorized"
        if status_code == 403:
            return "forbidden"
        if status_code == 404:
            return "not_found"
        if status_code >= 500:
            return "server_error"
        return f"request_failed_{status_code}"
