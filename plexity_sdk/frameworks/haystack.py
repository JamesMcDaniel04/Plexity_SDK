from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from ..graphrag import GraphRAGClient

BaseRetrieverType = Any
DocumentType = Any


@dataclass(frozen=True)
class HaystackRetrieverOptions:
    """Options for constructing a Haystack retriever backed by GraphRAG."""

    search_type: str = "hybrid"
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None

    def to_search_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.search_type:
            kwargs["search_type"] = self.search_type.lower()
        if self.max_tokens is not None:
            kwargs["max_tokens"] = int(self.max_tokens)
        if self.top_k is not None:
            limit = int(self.top_k)
            kwargs["max_entities"] = limit
            kwargs["max_communities"] = limit
        return kwargs


def _import_haystack() -> Tuple[Type[BaseRetrieverType], Type[DocumentType], str]:
    try:
        from haystack.components.retrievers import BaseRetriever  # type: ignore
        from haystack.dataclasses import Document  # type: ignore

        return BaseRetriever, Document, "components"
    except ImportError:
        try:
            from haystack.nodes import BaseRetriever  # type: ignore
            from haystack import Document  # type: ignore

            return BaseRetriever, Document, "legacy"
        except ImportError as exc:  # pragma: no cover - exercised in tests
            raise ImportError(
                "Haystack integration requires either `haystack-ai` (v2) or `farm-haystack` (v1). "
                "Install with `pip install haystack-ai` or `pip install farm-haystack`."
            ) from exc


def _transform_result(result: Any, document_ctor: Type[DocumentType]) -> List[DocumentType]:
    documents: List[DocumentType] = []
    payload = result if isinstance(result, dict) else {}
    context = payload.get("context", {}) if isinstance(payload, dict) else {}
    entities = context.get("entities", []) if isinstance(context, dict) else []
    confidence = payload.get("confidence")
    search_type = payload.get("search_type")

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        text = entity.get("description") or entity.get("name") or ""
        documents.append(
            document_ctor(
                content=text,
                meta={
                    "entity_id": entity.get("id"),
                    "entity_type": entity.get("type"),
                    "search_type": search_type,
                    "confidence": confidence,
                },
            )
        )
    return documents


def create_haystack_retriever(
    client: GraphRAGClient,
    options: Optional[HaystackRetrieverOptions] = None,
) -> BaseRetrieverType:
    """Return a Haystack retriever backed by the GraphRAGClient."""

    BaseRetriever, Document, _variant = _import_haystack()
    opts = options or HaystackRetrieverOptions()

    class GraphRAGHaystackRetriever(BaseRetriever):
        client: GraphRAGClient
        search_type: str = "hybrid"
        max_tokens: Optional[int] = None
        top_k: Optional[int] = None

        def _build_kwargs(self) -> Dict[str, Any]:
            kwargs: Dict[str, Any] = {}
            if self.search_type:
                kwargs["search_type"] = self.search_type
            if self.max_tokens is not None:
                kwargs["max_tokens"] = self.max_tokens
            if self.top_k is not None:
                kwargs["max_entities"] = self.top_k
                kwargs["max_communities"] = self.top_k
            return kwargs

        def _fetch(self, query: str) -> List[DocumentType]:
            result = self.client.search(query, **self._build_kwargs())
            documents = _transform_result(result, Document)
            if self.top_k is not None:
                return documents[: int(self.top_k)]
            return documents

        # Haystack v1 (farm-haystack) implements retrieve()
        def retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[DocumentType]:  # type: ignore[override]
            return self._fetch(query)

        # Haystack v1 calls _retrieve from BaseRetriever.retrieve()
        def _retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[DocumentType]:  # type: ignore[override]
            return self._fetch(query)

        # Haystack v2 components expect run()/arun()
        def run(self, query: str) -> Dict[str, Any]:  # type: ignore[override]
            documents = self._fetch(query)
            return {"documents": documents}

        async def arun(self, query: str) -> Dict[str, Any]:  # type: ignore[override]
            documents = await asyncio.to_thread(self._fetch, query)
            return {"documents": documents}

    return GraphRAGHaystackRetriever(
        client=client,
        search_type=opts.to_search_kwargs().get("search_type", "hybrid"),
        max_tokens=opts.max_tokens,
        top_k=opts.top_k,
    )
