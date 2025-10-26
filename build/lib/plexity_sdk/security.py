from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping, Optional

__all__ = [
    "AccessControlPolicy",
    "EncryptionContext",
    "ComplianceDirectiveType",
    "ComplianceDirective",
    "SecretReference",
]


@dataclass(frozen=True)
class AccessControlPolicy:
    """Models fine-grained access control for SDK operations."""

    tenant_id: str
    roles: Mapping[str, bool] = field(default_factory=dict)
    scopes: Mapping[str, str] = field(default_factory=dict)
    data_partition: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "tenantId": self.tenant_id,
            "roles": dict(self.roles),
            "scopes": dict(self.scopes),
        }
        if self.data_partition:
            payload["dataPartition"] = self.data_partition
        return payload


@dataclass(frozen=True)
class EncryptionContext:
    """Encryption guarantees for data in transit and at rest."""

    encrypt_in_transit: bool = True
    encrypt_at_rest: bool = True
    key_arn: Optional[str] = None
    kms_alias: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "encryptInTransit": self.encrypt_in_transit,
            "encryptAtRest": self.encrypt_at_rest,
        }
        if self.key_arn:
            payload["keyArn"] = self.key_arn
        if self.kms_alias:
            payload["kmsAlias"] = self.kms_alias
        return payload


class ComplianceDirectiveType(str, Enum):
    """Supported compliance operations."""

    DELETE_NODE = "delete_node"
    ANONYMIZE_NODE = "anonymize_node"
    DELETE_RELATIONSHIP = "delete_relationship"
    EXPORT_TENANT_DATA = "export_tenant_data"


@dataclass(frozen=True)
class ComplianceDirective:
    """Directive for compliance workflows (SOC2, GDPR, CCPA, etc.)."""

    directive: ComplianceDirectiveType
    payload: Mapping[str, object]
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        data: Dict[str, object] = {
            "directive": self.directive.value,
            "payload": dict(self.payload),
        }
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass(frozen=True)
class SecretReference:
    """Reference to a stored secret managed by the platform."""

    name: str
    version: Optional[str] = None
    provider: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {"name": self.name}
        if self.version:
            payload["version"] = self.version
        if self.provider:
            payload["provider"] = self.provider
        return payload
