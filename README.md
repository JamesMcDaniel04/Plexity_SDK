# Plexity Python SDK

Official Python bindings for the Plexity Agentic RAG Orchestrator API.

## Installation

```bash
pip install plexity-sdk
```

## Development & Testing

Install the SDK with development extras and run the verification suite:

```bash
pip install -e .[dev]
pytest
```

## Quickstart

```python
from plexity_sdk import PlexityClient

client = PlexityClient(
    base_url="https://api.plexity.ai",
    api_key="sqk_xxx.yyy"
)

workflows = client.list_workflows()
print(workflows)
```

See the full documentation in [docs/sdk-python.md](docs/sdk-python.md).

## GraphRAG Search

```python
from plexity_sdk import GraphRAGClient, PlexityClient

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_xxx.yyy")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")

result = rag.search(
    "Summarise the latest release milestones",
    use_microsoft_cli=True,
    microsoft_cli={"workspacePath": "/opt/graphrag/workspace"}
)

print(result["answer"])
```

Set `use_microsoft_cli=True` to delegate the query to the Microsoft GraphRAG CLI (with optional overrides passed under `microsoft_cli`). Omit the flag or set it to `False` to force the native orchestrator engine.

### Framework Integrations

The SDK ships optional helpers for popular retrieval frameworks:

```python
from plexity_sdk import create_langchain_retriever

retriever = create_langchain_retriever(
    client,
    org_id="org_default",
    environment="prod",
    top_k=5,
)

docs = retriever.get_relevant_documents("How do I rotate API keys?")
```

Similar helpers exist for LlamaIndex (`create_llamaindex_retriever`) and Haystack (`create_haystack_retriever`). Each factory accepts structured option dataclasses so you can override query settings per framework while delegating transport and telemetry to the SDK.
