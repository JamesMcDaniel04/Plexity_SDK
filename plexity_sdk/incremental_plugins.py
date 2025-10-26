from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Protocol

if TYPE_CHECKING:  # pragma: no cover
    from .graphrag import GraphRAGClient

__all__ = [
    "IncrementalIngestionPlugin",
    "register_incremental_ingestion_plugin",
    "get_incremental_ingestion_plugin",
    "list_incremental_ingestion_plugins",
    "invoke_incremental_ingestion_plugin",
]


class IncrementalIngestionPlugin(Protocol):
    """Callable signature for incremental ingestion plugins."""

    def __call__(self, client: "GraphRAGClient", slice_payload: Dict[str, Any]) -> Any:
        ...


_REGISTRY: Dict[str, IncrementalIngestionPlugin] = {}


def register_incremental_ingestion_plugin(
    name: str,
    handler: IncrementalIngestionPlugin,
    *,
    override: bool = False,
) -> None:
    """Register a plugin for incremental ingestion."""

    normalized = name.lower()
    if not override and normalized in _REGISTRY:
        raise ValueError(f"Plugin '{name}' is already registered")
    _REGISTRY[normalized] = handler


def get_incremental_ingestion_plugin(name: str) -> IncrementalIngestionPlugin:
    normalized = name.lower()
    if normalized not in _REGISTRY:
        raise KeyError(f"Plugin '{name}' is not registered")
    return _REGISTRY[normalized]


def list_incremental_ingestion_plugins() -> List[str]:
    return sorted(_REGISTRY.keys())


def invoke_incremental_ingestion_plugin(
    name: str,
    client: "GraphRAGClient",
    slice_payload: Dict[str, Any],
) -> Any:
    plugin = get_incremental_ingestion_plugin(name)
    return plugin(client, slice_payload)
