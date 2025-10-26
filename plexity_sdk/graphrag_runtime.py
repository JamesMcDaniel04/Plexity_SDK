from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Iterable, Mapping, Optional, Sequence, Set

__all__ = [
    "GraphRAGPackage",
    "GraphRAGFeature",
    "GraphRAGFeatureFlags",
    "GraphRAGRuntimeProfile",
    "resolve_runtime_profile",
]


class GraphRAGPackage(str, Enum):
    """Available package channels for the GraphRAG SDK runtime."""

    CORE = "core"
    ENTERPRISE = "enterprise"


class GraphRAGFeature(str, Enum):
    """Togglable GraphRAG feature flags."""

    PLUGIN_ENTRYPOINTS = "plugin_entrypoints"
    NEO4J_SUPPORT = "neo4j_support"
    SCHEMA_DIFF = "schema_diff"
    INCREMENTAL_JOB_ADVISOR = "incremental_job_advisor"
    ENTERPRISE_ADDONS = "enterprise_addons"


@dataclass(frozen=True)
class GraphRAGFeatureFlags:
    """Immutable set of enabled GraphRAG features."""

    enabled: FrozenSet[GraphRAGFeature]

    def __contains__(self, item: object) -> bool:
        return item in self.enabled

    def is_enabled(self, feature: GraphRAGFeature) -> bool:
        return feature in self.enabled

    def to_dict(self) -> Mapping[str, bool]:
        return {feature.value: True for feature in self.enabled}


@dataclass(frozen=True)
class GraphRAGRuntimeProfile:
    """Resolved runtime profile tying packages to feature flags."""

    package: GraphRAGPackage
    feature_flags: GraphRAGFeatureFlags
    optional_dependencies: FrozenSet[str]

    def requires_dependency(self, name: str) -> bool:
        return name in self.optional_dependencies


_PACKAGE_DEFAULTS: Mapping[GraphRAGPackage, FrozenSet[GraphRAGFeature]] = {
    GraphRAGPackage.CORE: frozenset({GraphRAGFeature.PLUGIN_ENTRYPOINTS}),
    GraphRAGPackage.ENTERPRISE: frozenset(
        {
            GraphRAGFeature.PLUGIN_ENTRYPOINTS,
            GraphRAGFeature.NEO4J_SUPPORT,
            GraphRAGFeature.SCHEMA_DIFF,
            GraphRAGFeature.INCREMENTAL_JOB_ADVISOR,
            GraphRAGFeature.ENTERPRISE_ADDONS,
        }
    ),
}

_FEATURE_DEPENDENCIES: Mapping[GraphRAGFeature, FrozenSet[str]] = {
    GraphRAGFeature.NEO4J_SUPPORT: frozenset({"neo4j>=5.16"}),
    GraphRAGFeature.SCHEMA_DIFF: frozenset({"neo4j>=5.16"}),
    GraphRAGFeature.INCREMENTAL_JOB_ADVISOR: frozenset(),
    GraphRAGFeature.PLUGIN_ENTRYPOINTS: frozenset(),
    GraphRAGFeature.ENTERPRISE_ADDONS: frozenset(),
}


def resolve_runtime_profile(
    package: GraphRAGPackage | str,
    *,
    enable: Optional[Iterable[GraphRAGFeature | str]] = None,
    disable: Optional[Iterable[GraphRAGFeature | str]] = None,
) -> GraphRAGRuntimeProfile:
    """Resolve a runtime profile for the given package channel.

    Args:
        package: Package identifier (`core` or `enterprise`).
        enable: Extra features to enable regardless of package defaults.
        disable: Features to disable from the resulting profile.
    """

    package_enum = GraphRAGPackage(package)
    defaults = set(_PACKAGE_DEFAULTS[package_enum])

    def _normalize(values: Optional[Iterable[GraphRAGFeature | str]]) -> Set[GraphRAGFeature]:
        resolved: Set[GraphRAGFeature] = set()
        if not values:
            return resolved
        for value in values:
            resolved.add(GraphRAGFeature(value))
        return resolved

    defaults.update(_normalize(enable))
    defaults.difference_update(_normalize(disable))
    frozen = frozenset(defaults)
    flags = GraphRAGFeatureFlags(enabled=frozen)

    optional_dependencies: Set[str] = set()
    for feature in frozen:
        optional_dependencies.update(_FEATURE_DEPENDENCIES.get(feature, ()))

    return GraphRAGRuntimeProfile(
        package=package_enum,
        feature_flags=flags,
        optional_dependencies=frozenset(optional_dependencies),
    )
