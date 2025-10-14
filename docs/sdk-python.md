# Plexity Python SDK

The `plexity-sdk` package makes it easy for data science and ML teams to orchestrate workflows, monitor executions, and validate webhooks from Python applications.

## Installation

```bash
pip install plexity-sdk
```

## Client Usage

```python
from plexity_sdk import PlexityClient

client = PlexityClient(
    base_url="https://api.plexity.ai",
    api_key="sqk_...",
)

workflows = client.list_workflows()
print([wf["workflow_id"] for wf in workflows])
```

### Executions

```python
execution = client.start_execution(
    workflow_id="team_task_delegation_default",
    input={"trigger": {"body": {"goal": "Compile weekly metrics"}}},
)

status = client.get_execution(execution["id"])
print(status["status"])
```

### Pagination & Filters

```python
recent_failures = client.list_executions(status=["failed"], limit=20)
```

### Cancel & Resume

```python
client.cancel_execution(execution_id)
client.resume_step(token="wait-step-token", payload={"approved": True})
```

## Webhook Validation

```python
from plexity_sdk import verify_webhook_signature, extract_webhook_request

def handle_request(headers, body, raw_body=None):
    webhook = extract_webhook_request(headers, body, raw_body)
    if not verify_webhook_signature(
        secret="your-shared-secret",
        payload=webhook["payload"],
        timestamp=webhook["timestamp"],
        signature=webhook["signature"],
    ):
        raise ValueError("Invalid webhook signature")
    # Continue processing...
```

## Error Handling

API errors raise `PlexityError` with `status_code` and `payload` attributes.

```python
from plexity_sdk import PlexityError

try:
    client.get_execution("missing")
except PlexityError as err:
    if err.status_code == 404:
        print("Execution not found")
```

## Advanced Usage

- Provide a custom `requests.Session` to reuse connections or bind retry adapters.
- Override `timeout` (seconds) when initialising the client.
- Call `list_triggers()` to retrieve webhook endpoints (including secrets) for the authenticated organization.

Refer to `docs/integration-guides/fastapi.md` for a FastAPI example using the Python SDK plus webhook validation.

## GraphRAG Operations

The SDK now exposes GraphRAG helpers for search, indexing, and graph inspection. Use `GraphRAGClient` to bind a default organization / environment context and delegate operations to either the native orchestrator or the Microsoft GraphRAG CLI.

```python
from plexity_sdk import GraphRAGClient, PlexityClient

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")

result = rag.search(
    "What changed in the latest rollout?",
    use_microsoft_cli=True,
    microsoft_cli={"workspacePath": "/opt/graphrag/workspace"}
)

print(result["answer"])
```

- `use_microsoft_cli=True` delegates the query to the Microsoft GraphRAG CLI (optionally pass CLI overrides via `microsoft_cli`).
- Set `use_microsoft_cli=False` or omit the flag to force the native orchestrator engine.
- All options accepted by `PlexityClient.search_graphrag` can be forwarded to `GraphRAGClient.search` as keyword arguments.

Additional helpers:

```python
# Full or incremental indexing
rag.index_documents(docs, mode="full")
rag.incremental_index(docs, detect_changes=True)

# Graph analytics
stats = rag.stats()
entities = rag.entities(query="Feature Flag")
communities = rag.communities(limit=10)
```

If you prefer to work directly with the HTTP client, the following wrappers are available:

```python
client.search_graphrag("Where are API keys documented?", use_microsoft_cli=False)
client.index_graphrag(docs, org_id="org_default")
client.get_graphrag_stats(org_id="org_default")
client.get_graphrag_entities(query="Incident", limit=5)
client.get_graphrag_communities(limit=10, environment="staging")
```

All methods accept optional `config_overrides` which are merged into the request payload without mutating the original object.

## Running Tests

Unit tests for the Python SDK live under `sdks/python/tests`. Execute them with:

```bash
cd sdks/python
python -m unittest discover
```

## Publishing to PyPI

1. Bump the version in `sdks/python/pyproject.toml`.
2. Build the distribution artifacts:

   ```bash
   cd sdks/python
   python -m build
   ```

3. Upload the wheel and sdist with Twine:

   ```bash
   twine upload dist/*
   ```

Ensure tests pass before publishing and that API keys / CLI overrides are omitted from version control.
