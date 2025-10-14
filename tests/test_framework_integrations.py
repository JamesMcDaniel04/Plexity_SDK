from __future__ import annotations

import asyncio
import sys
import types
import unittest
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Tuple

from plexity_sdk.frameworks import (
    HaystackRetrieverOptions,
    LangChainRetrieverOptions,
    LlamaIndexRetrieverOptions,
    create_haystack_retriever,
    create_langchain_retriever,
    create_llamaindex_retriever,
)


class StubGraphRAGClient:
    def __init__(self, result: Dict[str, Any]) -> None:
        self._result = result
        self.calls: List[Tuple[str, Dict[str, Any]]] = []

    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append((query, kwargs))
        payload = dict(self._result)
        payload.setdefault("search_type", kwargs.get("search_type"))
        return payload


SAMPLE_RESULT: Dict[str, Any] = {
    "confidence": 0.82,
    "context": {
        "entities": [
            {
                "id": "entity-1",
                "name": "LangChain SDK",
                "type": "LIBRARY",
                "description": "Integration ready entity.",
            }
        ],
        "communities": [
            {"id": "community-9", "summary": "Community summary", "title": "Integrations", "level": 2}
        ],
        "relationships": [
            {
                "id": "rel-1",
                "source": "entity-1",
                "target": "entity-2",
                "type": "DEPENDS_ON",
                "description": "Relates to another entity.",
            }
        ],
    },
}


@contextmanager
def install_langchain_stub() -> Iterable[None]:
    module_retrievers = types.ModuleType("langchain_core.retrievers")
    module_documents = types.ModuleType("langchain_core.documents")
    module_callbacks = types.ModuleType("langchain_core.callbacks.manager")
    base_module = types.ModuleType("langchain_core")

    class BaseRetriever:
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Any]:
            raise NotImplementedError

        async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Any]:
            raise NotImplementedError

        def get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Any]:
            return self._get_relevant_documents(query, run_manager=run_manager)

        async def aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Any]:
            return await self._aget_relevant_documents(query, run_manager=run_manager)

    class Document:
        def __init__(self, page_content: str, metadata: Dict[str, Any] | None = None) -> None:
            self.page_content = page_content
            self.metadata = metadata or {}

    class CallbackManagerForRetrieverRun:  # pragma: no cover - placeholder
        pass

    module_retrievers.BaseRetriever = BaseRetriever
    module_documents.Document = Document
    module_callbacks.CallbackManagerForRetrieverRun = CallbackManagerForRetrieverRun

    installed = {
        "langchain_core": base_module,
        "langchain_core.retrievers": module_retrievers,
        "langchain_core.documents": module_documents,
        "langchain_core.callbacks": types.ModuleType("langchain_core.callbacks"),
        "langchain_core.callbacks.manager": module_callbacks,
    }

    try:
        for name, module in installed.items():
            sys.modules[name] = module
        yield
    finally:
        for name in installed:
            sys.modules.pop(name, None)


@contextmanager
def install_llamaindex_stub() -> Iterable[None]:
    module_retrievers = types.ModuleType("llama_index.core.retrievers")
    module_schema = types.ModuleType("llama_index.core.schema")
    base_module = types.ModuleType("llama_index")
    core_module = types.ModuleType("llama_index.core")

    class BaseRetriever:
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def _retrieve(self, query: str) -> List[Any]:
            raise NotImplementedError

        async def _aretrieve(self, query: str) -> List[Any]:
            raise NotImplementedError

        def retrieve(self, query: str) -> List[Any]:
            return self._retrieve(query)

        async def aretrieve(self, query: str) -> List[Any]:
            return await self._aretrieve(query)

    class TextNode:
        def __init__(self, *, id_: str, text: str, metadata: Dict[str, Any]) -> None:
            self.id_ = id_
            self.text = text
            self.metadata = metadata

    class NodeWithScore:
        def __init__(self, node: TextNode, score: float | None = None) -> None:
            self.node = node
            self.score = score

    module_retrievers.BaseRetriever = BaseRetriever
    module_schema.TextNode = TextNode
    module_schema.NodeWithScore = NodeWithScore

    path_prefixes = {
        "llama_index": base_module,
        "llama_index.core": core_module,
        "llama_index.core.retrievers": module_retrievers,
        "llama_index.core.schema": module_schema,
    }

    try:
        for name, module in path_prefixes.items():
            sys.modules[name] = module
        yield
    finally:
        for name in path_prefixes:
            sys.modules.pop(name, None)


@contextmanager
def install_haystack_stub() -> Iterable[None]:
    components_module = types.ModuleType("haystack.components")
    module_retrievers = types.ModuleType("haystack.components.retrievers")
    dataclasses_module = types.ModuleType("haystack.dataclasses")
    base_module = types.ModuleType("haystack")

    class BaseRetriever:
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def run(self, query: str) -> Dict[str, Any]:  # pragma: no cover - placeholder
            raise NotImplementedError

        async def arun(self, query: str) -> Dict[str, Any]:  # pragma: no cover - placeholder
            raise NotImplementedError

        def retrieve(self, query: str, filters: Dict[str, Any] | None = None) -> List[Any]:
            raise NotImplementedError

        def _retrieve(self, query: str, filters: Dict[str, Any] | None = None) -> List[Any]:
            raise NotImplementedError

    class Document:
        def __init__(self, content: str, meta: Dict[str, Any] | None = None) -> None:
            self.content = content
            self.meta = meta or {}

    module_retrievers.BaseRetriever = BaseRetriever
    dataclasses_module.Document = Document

    installed = {
        "haystack": base_module,
        "haystack.components": components_module,
        "haystack.components.retrievers": module_retrievers,
        "haystack.dataclasses": dataclasses_module,
    }

    try:
        for name, module in installed.items():
            sys.modules[name] = module
        yield
    finally:
        for name in installed:
            sys.modules.pop(name, None)


class FrameworkIntegrationTests(unittest.TestCase):
    def test_langchain_retriever_transforms_entities(self) -> None:
        client = StubGraphRAGClient(SAMPLE_RESULT)
        with install_langchain_stub():
            retriever = create_langchain_retriever(
                client,
                LangChainRetrieverOptions(search_type="hybrid", max_entities=5),
            )
            docs = retriever.get_relevant_documents("Summarise integrations")

            self.assertEqual(len(docs), 2)
            self.assertEqual(docs[0].metadata["entity_id"], "entity-1")
            self.assertEqual(docs[1].metadata["type"], "community")

            loop_result = asyncio.run(retriever.aget_relevant_documents("Summarise integrations"))
            self.assertEqual(len(loop_result), len(docs))

    def test_langchain_retriever_requires_dependency(self) -> None:
        client = StubGraphRAGClient(SAMPLE_RESULT)

        original_import = __import__

        def raising_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("langchain_core"):
                raise ImportError("missing module")
            return original_import(name, *args, **kwargs)

        try:
            builtins = sys.modules["builtins"]
            setattr(builtins, "__import__", raising_import)
            with self.assertRaises(ImportError):
                create_langchain_retriever(client)
        finally:
            setattr(sys.modules["builtins"], "__import__", original_import)

    def test_llamaindex_retriever_builds_nodes(self) -> None:
        client = StubGraphRAGClient(SAMPLE_RESULT)
        with install_llamaindex_stub():
            retriever = create_llamaindex_retriever(client, LlamaIndexRetrieverOptions(max_entities=1))
            nodes = retriever.retrieve("Find relationships")

            self.assertEqual(len(nodes), 2)
            first = nodes[0]
            self.assertEqual(first.node.metadata["type"], "entity")
            self.assertTrue(first.node.text.startswith("LangChain SDK"))

            async_nodes = asyncio.run(retriever.aretrieve("Find relationships"))
            self.assertEqual(len(async_nodes), len(nodes))

    def test_haystack_retriever_supports_run_and_retrieve(self) -> None:
        client = StubGraphRAGClient(SAMPLE_RESULT)
        with install_haystack_stub():
            retriever = create_haystack_retriever(client, HaystackRetrieverOptions(top_k=1))
            docs = retriever.retrieve("Launch checklist")
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].content, "Integration ready entity.")

            run_result = retriever.run("Launch checklist")
            self.assertIn("documents", run_result)
            self.assertEqual(len(run_result["documents"]), 1)

            async_result = asyncio.run(retriever.arun("Launch checklist"))
            self.assertEqual(len(async_result["documents"]), 1)


if __name__ == "__main__":
    unittest.main()
