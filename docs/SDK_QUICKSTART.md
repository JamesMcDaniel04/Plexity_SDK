# Plexity Python SDK Quickstart

Get up and running with the Plexity Agentic Orchestrator and GraphRAG tooling from Python in a few minutes. This guide covers installation, configuration, synchronous and asynchronous usage, and optional integrations.

---

## 1. Audience & Prerequisites

- **Audience:** Python teams building orchestrated RAG, automation workflows, and telemetry pipelines.
- **Python:** 3.9 or newer (3.10+ recommended).
- **Access:** A Plexity API key with workflow and GraphRAG permissions.
- **Optional:** Extras for LangChain, LlamaIndex, or Haystack integrations.

---

## 2. Installation Matrix

| Goal | Command | Notes |
| --- | --- | --- |
| Minimal install | `pip install plexity-sdk` | Installs the core HTTP client and helpers |
| Dev + tests | `pip install plexity-sdk[dev]` | Adds pytest and tooling used in this repo |
| LangChain helper | `pip install plexity-sdk[langchain]` | Pulls `langchain-core` |
| LlamaIndex helper | `pip install plexity-sdk[llamaindex]` | Pulls `llama-index` |
| Haystack helper | `pip install plexity-sdk[haystack]` | Supports haystack-ai or farm-haystack |
| All integrations | `pip install plexity-sdk[frameworks]` | Installs every optional framework |
| Async client | `pip install plexity-sdk[async]` | Installs `httpx` for async transport |
| GraphRAG core | `pip install plexity-sdk[graphrag-core]` | Feature flag scaffolding without extra deps |
| GraphRAG enterprise | `pip install plexity-sdk[graphrag-enterprise]` | Neo4j + storage + scheduler integrations |
| Enterprise bundle | `pip install plexity-sdk[enterprise]` | Superset of GraphRAG enterprise extras |
| S3 adapter | `pip install plexity-sdk[s3]` | Adds `boto3` for S3-compatible object storage |
| GCS adapter | `pip install plexity-sdk[gcs]` | Adds `google-cloud-storage` for GCS buckets |
| MinIO adapter | `pip install plexity-sdk[minio]` | Adds `minio` SDK for on-prem installations |
| Temporal scheduler | `pip install plexity-sdk[temporal]` | Adds `temporalio` async client |
| Argo workflows | `pip install plexity-sdk[argo]` | Uses `requests` to submit workflows via REST |

All extras are additive, so you can install multiple at once: `pip install plexity-sdk[enterprise,temporal]`.

---

## 3. Authenticate & Configure

```bash
export PLEXITY_API_KEY="sqk_your-key"
export PLEXITY_BASE_URL="https://api.plexity.ai"
```

You can also supply these values directly when constructing the client.

---

## 4. First Request

```python
from plexity_sdk import PlexityClient

client = PlexityClient(
    base_url="https://api.plexity.ai",
    api_key="sqk_your-key",
)

workflows = client.list_workflows()
print([wf["id"] for wf in workflows])
```

Wrap the client in a context manager to ensure the underlying `requests.Session` is closed:

```python
with PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_your-key") as client:
    execution = client.start_execution(
        workflow_id="team_task_delegation_default",
        input={"trigger": {"body": {"goal": "Compile weekly metrics"}}},
    )
    status = client.get_execution(execution["id"])
    print(status["status"])
```

---

## 5. GraphRAG Essentials

```python
from plexity_sdk import (
    GraphRAGClient,
    LangChainRetrieverOptions,
    PlexityClient,
    create_langchain_retriever,
)

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_your-key")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")

search_result = rag.search("What changed in the latest rollout?")
print(search_result["answer"])

retriever = create_langchain_retriever(
    rag,
    options=LangChainRetrieverOptions(max_entities=5, max_communities=5),
)
documents = retriever.get_relevant_documents("Where do I configure webhooks?")
```

If you want to offload heavy GraphRAG operations to the Microsoft CLI, call `ensure_microsoft_graphrag_runtime()` once during provisioning to bootstrap an isolated virtual environment. The helper skips reinstalling packages when the runtime already exists and raises descriptive errors if provisioning fails.

---

## 6. Asynchronous Workflows

Install the async extra (`pip install plexity-sdk[async]`) and use the `AsyncPlexityClient` wrapper to issue non-blocking HTTP requests via `httpx.AsyncClient`:

```python
import asyncio
from plexity_sdk import AsyncPlexityClient

async def main():
    async with AsyncPlexityClient(
        base_url="https://api.plexity.ai",
        api_key="sqk_your-key",
        max_retries=2,
    ) as client:
        workflows = await client.list_workflows()
        print(workflows)

asyncio.run(main())
```

Every REST method exposed by `PlexityClient` has a coroutine twin on `AsyncPlexityClient`, so you can `await` calls like `search_graphrag`, `index_graphrag`, or `list_workflows` without thread pools.

---

## 7. Next Steps

- Validate incoming webhooks with `verify_webhook_signature` and `extract_webhook_request`.
- Record GraphRAG telemetry events using `GraphRAGTelemetry`.
- Explore automation helpers `IntegrationAutomationClient` and `ClaudeAutomationClient` for repository orchestration.
- Review the extended usage guide in `docs/sdk-python.md` and the FastAPI example in `docs/integration-guides/fastapi.md`.
