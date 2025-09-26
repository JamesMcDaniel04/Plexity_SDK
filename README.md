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

See the full documentation in `docs/integration-guides/python.md`.
