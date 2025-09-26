from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional

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
