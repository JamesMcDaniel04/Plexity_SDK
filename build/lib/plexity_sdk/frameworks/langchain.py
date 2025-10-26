from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from ..graphrag import GraphRAGClient

DocumentType = Any
BaseRetrieverType = Any
CallbackManagerType = Any


@dataclass(frozen=True)
class LangChainRetrieverOptions:
    """Options that mirror the LangChain connector available in the JS SDK."""

    search_type: str = "hybrid"
    max_tokens: Optional[int] = None
    max_entities: Optional[int] = None
    max_communities: Optional[int] = None

    def to_search_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.search_type:
            kwargs["search_type"] = self.search_type.lower()
        if self.max_tokens is not None:
            kwargs["max_tokens"] = int(self.max_tokens)
        if self.max_entities is not None:
            kwargs["max_entities"] = int(self.max_entities)
        if self.max_communities is not None:
            kwargs["max_communities"] = int(self.max_communities)
        return kwargs


def _import_langchain() -> Tuple[BaseRetrieverType, Type[DocumentType], CallbackManagerType]:
    try:
        from langchain_core.documents import Document  # type: ignore
        from langchain_core.retrievers import BaseRetriever  # type: ignore
        from langchain_core.callbacks.manager import (  # type: ignore
            CallbackManagerForRetrieverRun,
        )
    except ImportError as exc:  # pragma: no cover - exercised in tests
        raise ImportError(
            "LangChain integration requires the `langchain-core` package. "
            "Install it with `pip install langchain-core`."
        ) from exc

    return BaseRetriever, Document, CallbackManagerForRetrieverRun


def _transform_result(result: Any, document_ctor: Type[DocumentType]) -> List[DocumentType]:
    documents: List[DocumentType] = []

    context = (result or {}).get("context", {}) if isinstance(result, dict) else {}
    entities = context.get("entities", []) if isinstance(context, dict) else []
    communities = context.get("communities", []) if isinstance(context, dict) else []
    confidence = (result or {}).get("confidence")
    search_type = (result or {}).get("search_type")

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        page_content = entity.get("description") or entity.get("name") or ""
        documents.append(
            document_ctor(
                page_content=page_content,
                metadata={
                    "type": "entity",
                    "entity_id": entity.get("id"),
                    "name": entity.get("name"),
                    "entity_type": entity.get("type"),
                    "search_type": search_type,
                    "confidence": confidence,
                },
            )
        )

    for community in communities:
        if not isinstance(community, dict):
            continue
        summary = community.get("summary") or community.get("title") or ""
        documents.append(
            document_ctor(
                page_content=summary,
                metadata={
                    "type": "community",
                    "community_id": community.get("id"),
                    "title": community.get("title"),
                    "level": community.get("level"),
                    "search_type": search_type,
                    "confidence": confidence,
                },
            )
        )

    return documents


def create_langchain_retriever(
    client: GraphRAGClient,
    options: Optional[LangChainRetrieverOptions] = None,
) -> BaseRetrieverType:
    """Return a LangChain retriever backed by the GraphRAGClient."""

    BaseRetriever, Document, CallbackManagerForRetrieverRun = _import_langchain()
    opts = options or LangChainRetrieverOptions()

    class GraphRAGLangChainRetriever(BaseRetriever):
        client: GraphRAGClient
        search_type: str = "hybrid"
        max_tokens: Optional[int] = None
        max_entities: Optional[int] = None
        max_communities: Optional[int] = None

        def _get_relevant_documents(
            self,
            query: str,
            *,
            run_manager: Optional[CallbackManagerForRetrieverRun] = None,
        ) -> List[DocumentType]:
            kwargs: Dict[str, Any] = {}
            if self.search_type:
                kwargs["search_type"] = self.search_type
            if self.max_tokens is not None:
                kwargs["max_tokens"] = self.max_tokens
            if self.max_entities is not None:
                kwargs["max_entities"] = self.max_entities
            if self.max_communities is not None:
                kwargs["max_communities"] = self.max_communities
            result = self.client.search(query, **kwargs)
            return _transform_result(result, Document)

        async def _aget_relevant_documents(
            self,
            query: str,
            *,
            run_manager: Optional[CallbackManagerForRetrieverRun] = None,
        ) -> List[DocumentType]:
            return await asyncio.to_thread(self._get_relevant_documents, query, run_manager=run_manager)

    return GraphRAGLangChainRetriever(
        client=client,
        search_type=opts.to_search_kwargs().get("search_type", "hybrid"),
        max_tokens=opts.max_tokens,
        max_entities=opts.max_entities,
        max_communities=opts.max_communities,
    )
