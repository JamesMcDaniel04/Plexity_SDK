from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from ..graphrag import GraphRAGClient

BaseRetrieverType = Any
NodeWithScoreType = Any
TextNodeType = Any


@dataclass(frozen=True)
class LlamaIndexRetrieverOptions:
    """Options for building a LlamaIndex retriever backed by GraphRAG."""

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


def _import_llamaindex() -> Tuple[Type[BaseRetrieverType], Type[NodeWithScoreType], Type[TextNodeType]]:
    try:
        from llama_index.core.retrievers import BaseRetriever  # type: ignore
        from llama_index.core.schema import NodeWithScore, TextNode  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in tests
        raise ImportError(
            "LlamaIndex integration requires the `llama-index` package. "
            "Install it with `pip install llama-index`."
        ) from exc

    return BaseRetriever, NodeWithScore, TextNode


def _build_node_text(entity: Dict[str, Any], relationships: List[Dict[str, Any]]) -> str:
    summary: List[str] = []
    name = entity.get("name")
    if name:
        summary.append(str(name))
    description = entity.get("description")
    if description:
        summary.append(str(description))

    related: List[str] = []
    entity_id = entity.get("id")
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        if rel.get("source") != entity_id and rel.get("target") != entity_id:
            continue
        rel_type = rel.get("type") or rel.get("relationship_type") or "RELATES_TO"
        description = rel.get("description") or ""
        related.append(f"{rel_type}: {description}".strip())

    if related:
        summary.append("; ".join(related))
    return "\n".join(summary)


def _transform_result(
    result: Any,
    node_with_score_ctor: Type[NodeWithScoreType],
    text_node_ctor: Type[TextNodeType],
) -> List[NodeWithScoreType]:
    nodes: List[NodeWithScoreType] = []
    payload = result if isinstance(result, dict) else {}
    context = payload.get("context", {}) if isinstance(payload, dict) else {}
    entities = context.get("entities", []) if isinstance(context, dict) else []
    communities = context.get("communities", []) if isinstance(context, dict) else []
    relationships = context.get("relationships", []) if isinstance(context, dict) else []
    confidence = payload.get("confidence")

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        text = _build_node_text(entity, relationships if isinstance(relationships, list) else [])
        node = text_node_ctor(
            id_=entity.get("id"),
            text=text,
            metadata={
                "type": "entity",
                "entity_type": entity.get("type"),
                "name": entity.get("name"),
                "confidence": confidence,
            },
        )
        nodes.append(node_with_score_ctor(node, score=confidence))

    for community in communities:
        if not isinstance(community, dict):
            continue
        node = text_node_ctor(
            id_=community.get("id"),
            text=community.get("summary") or community.get("title") or "",
            metadata={
                "type": "community",
                "level": community.get("level"),
                "title": community.get("title"),
                "confidence": confidence,
            },
        )
        nodes.append(node_with_score_ctor(node, score=confidence))

    return nodes


def create_llamaindex_retriever(
    client: GraphRAGClient,
    options: Optional[LlamaIndexRetrieverOptions] = None,
) -> BaseRetrieverType:
    """Return a LlamaIndex retriever backed by the GraphRAGClient."""

    BaseRetriever, NodeWithScore, TextNode = _import_llamaindex()
    opts = options or LlamaIndexRetrieverOptions()

    class GraphRAGLlamaIndexRetriever(BaseRetriever):
        client: GraphRAGClient
        search_type: str = "hybrid"
        max_tokens: Optional[int] = None
        max_entities: Optional[int] = None
        max_communities: Optional[int] = None

        def _retrieve(self, query: str) -> List[NodeWithScoreType]:
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
            return _transform_result(result, NodeWithScore, TextNode)

        async def _aretrieve(self, query: str) -> List[NodeWithScoreType]:
            return await asyncio.to_thread(self._retrieve, query)

    return GraphRAGLlamaIndexRetriever(
        client=client,
        search_type=opts.to_search_kwargs().get("search_type", "hybrid"),
        max_tokens=opts.max_tokens,
        max_entities=opts.max_entities,
        max_communities=opts.max_communities,
    )
