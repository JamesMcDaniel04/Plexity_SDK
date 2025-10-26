from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import pytest

from plexity_sdk.graphrag import GraphRAGClient
from plexity_sdk.graphrag_runtime import GraphRAGFeature, GraphRAGPackage
from plexity_sdk.orchestration import InMemoryJobScheduler, JobState
from plexity_sdk.security import (
    AccessControlPolicy,
    ComplianceDirective,
    ComplianceDirectiveType,
    EncryptionContext,
)
from plexity_sdk.storage import StorageAdapter, StorageObject


class DummyStorageAdapter(StorageAdapter):
    def __init__(self) -> None:
        self._store: Dict[str, StorageObject] = {}

    def put_object(
        self,
        key: str,
        data: bytes,
        *,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageObject:
        obj = StorageObject(key=key, data=data, metadata=metadata or {})
        self._store[key] = obj
        return obj

    def get_object(self, key: str) -> StorageObject:
        return self._store[key]

    def delete_object(self, key: str) -> None:
        self._store.pop(key, None)


class FakeClient:
    def __init__(self) -> None:
        self.recommend_payload: Optional[Dict[str, Any]] = None
        self.created_job_payload: Optional[Dict[str, Any]] = None
        self.trigger_payload: Optional[Dict[str, Any]] = None
        self.compliance_payload: Optional[Dict[str, Any]] = None

    def recommend_graphrag_job_slices(self, **kwargs: Any):
        self.recommend_payload = kwargs
        return [{"label": "Customer", "orgId": kwargs.get("org_id")}]

    def create_graphrag_incremental_job(self, **payload: Any):
        self.created_job_payload = payload
        return {"job_id": "job-123"}

    def trigger_graphrag_incremental_job_slice(self, **payload: Any):
        self.trigger_payload = payload
        return {"status": "queued"}

    def apply_graphrag_compliance_directive(self, **payload: Any):
        self.compliance_payload = payload
        return {"accepted": True}

    def probe_endpoint(self, method: str, path: str, *, timeout: Optional[float] = None) -> bool:
        return True


def _enterprise_client(fake: FakeClient) -> GraphRAGClient:
    client = GraphRAGClient(
        fake,
        org_id="orgA",
        environment="prod",
        team_id="teamX",
        graph_id="primary",
        shard_id="shard-01",
        package=GraphRAGPackage.ENTERPRISE,
    )
    client.set_scheduler(InMemoryJobScheduler())
    adapter = DummyStorageAdapter()
    client.register_storage_adapter("memory", adapter)
    client.set_default_storage_adapter("memory")
    client.update_context(
        access_policy=AccessControlPolicy(
            tenant_id="orgA",
            roles={"maintainer": True},
            scopes={"cluster": "prod"},
            data_partition="p0",
        ),
        encryption=EncryptionContext(
            encrypt_in_transit=True,
            encrypt_at_rest=True,
            kms_alias="alias/plexity/graphrag",
        ),
    )
    return client


def test_recommendations_and_context_merging():
    fake = FakeClient()
    client = _enterprise_client(fake)
    result = client.recommend_incremental_job_slices(labels=["Customer"])
    assert result[0]["label"] == "Customer"
    assert fake.recommend_payload is not None
    assert fake.recommend_payload["org_id"] == "orgA"
    assert fake.recommend_payload["environment"] == "prod"
    assert fake.recommend_payload["labels"] == ["Customer"]
    assert fake.recommend_payload["graph_id"] == "primary"
    assert fake.recommend_payload["shard_id"] == "shard-01"
    assert fake.recommend_payload["access_policy"]["tenantId"] == "orgA"


def test_storage_offload_roundtrip():
    fake = FakeClient()
    client = _enterprise_client(fake)
    stored = client.offload_intermediate_state("jobs/customer.json", {"hello": "world"})
    assert stored.key == "jobs/customer.json"
    retrieved = client.retrieve_intermediate_state("jobs/customer.json")
    assert retrieved.as_text()
    assert "hello" in retrieved.as_text()
    client.delete_intermediate_state("jobs/customer.json")
    with pytest.raises(KeyError):
        client.retrieve_intermediate_state("jobs/customer.json")


def test_schedule_incremental_job_and_status():
    fake = FakeClient()
    client = _enterprise_client(fake)
    handle = client.schedule_incremental_job(
        "IncrementalIndexer",
        {"slice": {"label": "Customer"}},
        idempotency_key="customer-orgA",
        tags={"batch": "nightly"},
    )
    assert handle.reference == "customer-orgA"
    status = client.get_scheduled_job_status(handle)
    assert status.state == JobState.PENDING
    assert fake.created_job_payload is None  # scheduler path bypasses HTTP client


@pytest.mark.asyncio
async def test_async_scheduler_entrypoints():
    fake = FakeClient()
    client = _enterprise_client(fake)
    handle = await client.schedule_incremental_job_async(
        "IncrementalIndexer",
        {"slice": {"label": "Customer"}},
    )
    status = await client.get_scheduled_job_status_async(handle)
    assert status.reference == handle.reference
    await client.cancel_scheduled_job_async(handle)
    cancelled = await client.get_scheduled_job_status_async(handle)
    assert cancelled.state == JobState.CANCELLED


def test_incremental_job_creation_and_compliance_calls():
    fake = FakeClient()
    client = _enterprise_client(fake)

    client.create_incremental_job(
        {"slice": {"label": "Customer"}},
        idempotency_key="job-1",
        job_labels=["Customer"],
    )
    assert fake.created_job_payload is not None
    assert fake.created_job_payload["idempotency_key"] == "job-1"
    assert fake.created_job_payload["job_labels"] == ["Customer"]

    client.trigger_incremental_job_slice(
        {"job_id": "job-1", "slice_id": "slice-1"},
        idempotency_key="slice-1",
    )
    assert fake.trigger_payload is not None
    assert fake.trigger_payload["idempotency_key"] == "slice-1"

    directive = ComplianceDirective(
        directive=ComplianceDirectiveType.DELETE_NODE,
        payload={"nodeId": "customer:123"},
        reason="GDPR request",
    )
    client.apply_compliance_directive(directive)
    assert fake.compliance_payload is not None
    assert fake.compliance_payload["directive"]["directive"] == "delete_node"
    assert fake.compliance_payload["org_id"] == "orgA"
    assert fake.compliance_payload["graph_id"] == "primary"
    assert fake.compliance_payload["access_policy"]["tenantId"] == "orgA"


def test_feature_flags_include_enterprise_addons():
    fake = FakeClient()
    client = _enterprise_client(fake)
    assert client.feature_flags.is_enabled(GraphRAGFeature.ENTERPRISE_ADDONS)


def test_backend_validation_detects_missing_routes():
    class MissingRouteClient(FakeClient):
        def probe_endpoint(self, method: str, path: str, *, timeout: Optional[float] = None) -> bool:
            if "compliance" in path:
                return False
            return True

    with pytest.raises(RuntimeError) as exc:
        GraphRAGClient(
            MissingRouteClient(),
            org_id="orgA",
            environment="prod",
            team_id="teamX",
            graph_id="primary",
            shard_id="shard-01",
            package=GraphRAGPackage.ENTERPRISE,
        )

    assert "enterprise_addons" in str(exc.value)
