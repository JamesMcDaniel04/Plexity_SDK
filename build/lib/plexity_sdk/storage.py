from __future__ import annotations

import base64
from dataclasses import dataclass
import io
from typing import Any, Dict, Iterable, List, Optional, Protocol, runtime_checkable

__all__ = [
    "StorageObject",
    "StorageAdapter",
    "StorageAdapterRegistry",
    "S3StorageAdapter",
    "GCSStorageAdapter",
    "MinIOStorageAdapter",
]


@dataclass
class StorageObject:
    """Represents an object stored via a storage adapter."""

    key: str
    data: bytes
    metadata: Dict[str, str]

    def as_text(self, encoding: str = "utf-8") -> str:
        return self.data.decode(encoding)

    def as_base64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


@runtime_checkable
class StorageAdapter(Protocol):
    """Protocol for pluggable object storage adapters."""

    def put_object(self, key: str, data: bytes, *, metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        ...

    def get_object(self, key: str) -> StorageObject:
        ...

    def delete_object(self, key: str) -> None:
        ...


class StorageAdapterRegistry:
    """Registry for named storage adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, StorageAdapter] = {}

    def register(self, name: str, adapter: StorageAdapter, *, override: bool = False) -> None:
        normalized = name.lower()
        if not override and normalized in self._adapters:
            raise ValueError(f"Storage adapter '{name}' is already registered")
        self._adapters[normalized] = adapter

    def get(self, name: str) -> StorageAdapter:
        normalized = name.lower()
        if normalized not in self._adapters:
            raise KeyError(f"Storage adapter '{name}' is not registered")
        return self._adapters[normalized]

    def list(self) -> List[str]:
        return sorted(self._adapters.keys())


def _require_boto3() -> Any:
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Install plexity-sdk[s3] or plexity-sdk[enterprise] to use the S3 storage adapter"
        ) from exc
    return boto3


def _require_gcs() -> Any:
    try:
        from google.cloud import storage  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Install plexity-sdk[gcs] or plexity-sdk[enterprise] to use the GCS storage adapter"
        ) from exc
    return storage


def _require_minio() -> Any:
    try:
        from minio import Minio  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Install plexity-sdk[minio] or plexity-sdk[enterprise] to use the MinIO storage adapter"
        ) from exc
    return Minio


class S3StorageAdapter:
    """AWS S3 adapter built on top of boto3."""

    def __init__(
        self,
        bucket: str,
        *,
        client: Any = None,
        extra_client_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        boto3 = _require_boto3()
        self._bucket = bucket
        self._client = client or boto3.client("s3", **(extra_client_kwargs or {}))

    def put_object(self, key: str, data: bytes, *, metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        meta = metadata or {}
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, Metadata=meta)
        return StorageObject(key=key, data=data, metadata=meta)

    def get_object(self, key: str) -> StorageObject:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        body = resp["Body"].read()
        metadata = resp.get("Metadata", {})
        return StorageObject(key=key, data=body, metadata=metadata)

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class GCSStorageAdapter:
    """Google Cloud Storage adapter."""

    def __init__(
        self,
        bucket: str,
        *,
        client: Any = None,
        extra_client_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        storage = _require_gcs()
        self._bucket_name = bucket
        self._client = client or storage.Client(**(extra_client_kwargs or {}))
        self._bucket = self._client.bucket(bucket)

    def put_object(self, key: str, data: bytes, *, metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        blob = self._bucket.blob(key)
        blob.metadata = metadata or {}
        blob.upload_from_string(data)
        return StorageObject(key=key, data=data, metadata=blob.metadata or {})

    def get_object(self, key: str) -> StorageObject:
        blob = self._bucket.blob(key)
        data = blob.download_as_bytes()
        metadata = blob.metadata or {}
        return StorageObject(key=key, data=data, metadata=metadata)

    def delete_object(self, key: str) -> None:
        blob = self._bucket.blob(key)
        blob.delete()


class MinIOStorageAdapter:
    """On-prem MinIO adapter leveraging the MinIO Python SDK."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = True,
        region: Optional[str] = None,
    ) -> None:
        Minio = _require_minio()
        self._bucket = bucket
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )
        if not self._client.bucket_exists(bucket):  # pragma: no cover - network side effect
            self._client.make_bucket(bucket)

    def put_object(self, key: str, data: bytes, *, metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        stream = io.BytesIO(data)
        self._client.put_object(self._bucket, key, stream, len(data), metadata=metadata or {})
        return StorageObject(key=key, data=data, metadata=metadata or {})

    def get_object(self, key: str) -> StorageObject:
        response = self._client.get_object(self._bucket, key)
        try:
            body = response.read()
        finally:  # pragma: no branch
            response.close()
            response.release_conn()
        headers = dict(getattr(response, "headers", {}) or {})
        metadata = {str(key): str(value) for key, value in headers.items()}
        return StorageObject(key=key, data=body, metadata=metadata)

    def delete_object(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)
