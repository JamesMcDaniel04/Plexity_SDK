from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

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
