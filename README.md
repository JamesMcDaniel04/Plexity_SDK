# SprintIQ Python SDK

Official Python bindings for the SprintIQ Agentic RAG Orchestrator API.

## Installation

```bash
pip install sprintiq-sdk
```

## Quickstart

```python
from sprintiq_sdk import SprintIQClient

client = SprintIQClient(
    base_url="https://api.sprintiq.ai",
    api_key="sqk_xxx.yyy"
)

workflows = client.list_workflows()
print(workflows)
```

See the full documentation in [docs/sdk-python.md](../../docs/sdk-python.md).

## GraphRAG Search

```python
from sprintiq_sdk import GraphRAGClient, SprintIQClient

client = SprintIQClient(base_url="https://api.sprintiq.ai", api_key="sqk_xxx.yyy")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")

result = rag.search(
    "Summarise the latest release milestones",
    use_microsoft_cli=True,
    microsoft_cli={"workspacePath": "/opt/graphrag/workspace"}
)

print(result["answer"])
```

Set `use_microsoft_cli=True` to delegate the query to the Microsoft GraphRAG CLI (with optional overrides passed under `microsoft_cli`). Omit the flag or set it to `False` to force the native orchestrator engine.
