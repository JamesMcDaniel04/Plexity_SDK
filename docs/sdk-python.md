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

Refer to [`docs/integration-guides/fastapi.md`](integration-guides/fastapi.md) for a FastAPI example using the Python SDK plus webhook validation.

## GraphRAG Operations

The SDK now exposes GraphRAG helpers for search, indexing, and graph inspection. Use `GraphRAGClient` to bind a default organization / environment context and delegate operations to either the native orchestrator or the Microsoft GraphRAG CLI.

```python
from plexity_sdk import GraphRAGClient, PlexityClient

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")
rag.validate_backend_support()  # ensures enterprise/incremental routes exist

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
- `GraphRAGClient` automatically probes the orchestrator for enterprise and incremental job routes. Call `validate_backend_support()` to inspect capabilities or pass `validate_backend_support=False` when working with mock clients.

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

### Enterprise GraphRAG Extensions

- Select runtime packages explicitly via `GraphRAGClient(..., package="core"|"enterprise")` and toggle granular feature flags with `enable_features` / `disable_features`.
- Install `plexity-sdk[graphrag-enterprise]` to pull the Neo4j driver required for schema diff tooling and on-box recommendations.
- Use the Neo4j helpers to snapshot schemas, plan migrations, and execute transactional batches:

```python
from plexity_sdk import (
    GraphRAGClient,
    GraphRAGPackage,
    Neo4jConnectionConfig,
)

graphrag = GraphRAGClient(client, package=GraphRAGPackage.ENTERPRISE)
driver_manager = graphrag.create_neo4j_driver_manager(
    Neo4jConnectionConfig(
        uri="neo4j+s://demo.databases.neo4j.io",
        username="neo4j",
        password="secret",
    )
)
planner = graphrag.create_neo4j_schema_planner(driver_manager)
snapshot = graphrag.snapshot_neo4j_schema(planner)
plan = graphrag.plan_neo4j_schema_migration(planner, snapshot)
result = graphrag.apply_neo4j_schema_migration(
    graphrag.create_neo4j_batch_executor(driver_manager),
    plan,
    dry_run=True,
)
```

- Surface incremental job slices from the orchestrator or directly from Neo4j using `recommend_incremental_job_slices` and `recommend_neo4j_job_slices`.
- Wire ETL pipelines into GraphRAG incremental ingestion with `register_incremental_ingestion_plugin` and `GraphRAGClient.ingest_with_plugin`.

### Distributed Incremental Jobs

- Inject an orchestration backend (Temporal, Argo Workflows, or in-memory) via `GraphRAGClient.set_scheduler()`.
- Schedule long-running incremental updates with idempotency keys for exactly-once semantics:

```python
from plexity_sdk import GraphRAGClient, TemporalJobScheduler

scheduler = TemporalJobScheduler(
    target_host="tempo.example.com:7233",
    namespace="plexity",
    task_queue="graphrag-incremental",
)

graphrag.set_scheduler(scheduler)
handle = graphrag.schedule_incremental_job(
    "IncrementalIndexer",
    {"slice": {"label": "Customer", "org_id": "org_default"}},
    idempotency_key="customer-org_default-2024-07-01",
)
status = graphrag.get_scheduled_job_status(handle)
```

Use the async variants (`schedule_incremental_job_async`, `get_scheduled_job_status_async`) when running inside an event loop.

### Storage Offloading & Pluggable Compute

- Register storage adapters for S3, GCS, MinIO, or custom endpoints so intermediate state can land close to your compute cluster:

```python
from plexity_sdk import S3StorageAdapter

graphrag.register_storage_adapter(
    "s3",
    S3StorageAdapter(bucket="plexity-graphrag-intermediate"),
)
graphrag.set_default_storage_adapter("s3")
stored = graphrag.offload_intermediate_state("jobs/2024-07-01/customer.json", "{}")
```

- Retrieve or delete persisted slices with `retrieve_intermediate_state` / `delete_intermediate_state` to support distributed workers.
- Combine storage offload with multi-graph contexts by configuring `graph_id` / `shard_id` when instantiating `GraphRAGClient`.

### Security & Compliance

- Attach access policies and encryption contexts so every API call carries tenant isolation metadata:

```python
from plexity_sdk import AccessControlPolicy, EncryptionContext

graphrag.update_context(
    access_policy=AccessControlPolicy(
        tenant_id="org_default",
        roles={"reader": True, "maintainer": True},
        scopes={"environment": "prod"},
    ),
    encryption=EncryptionContext(encrypt_in_transit=True, encrypt_at_rest=True, kms_alias="alias/plexity/graphrag"),
)
```

- Execute GDPR/CCPA/SOC2 directives programmatically using `ComplianceDirective`:

```python
from plexity_sdk import ComplianceDirective, ComplianceDirectiveType

directive = ComplianceDirective(
    directive=ComplianceDirectiveType.DELETE_NODE,
    payload={"nodeId": "customer:123"},
    reason="Customer account deletion",
)
graphrag.apply_compliance_directive(directive)
```

- Reference platform-managed secrets inside ingestion plugins with `SecretReference` to avoid leaking credentials into pipelines.

## Running Tests

Unit tests for the Python SDK live under `tests`. Execute them with:

```bash
python -m pytest
```

## Publishing to PyPI

The SDK ships with automated release workflows. Follow the streamlined path:

1. Update `pyproject.toml` and `plexity_sdk/__init__.py` to the target version.
2. Run the test suite locally (`pytest`) and build artifacts (`python -m build`) as a sanity check.
3. Smoke-test the wheel in a clean virtual environment before publishing:

   ```bash
   python -m venv /tmp/plexity_sdk_release
   /tmp/plexity_sdk_release/bin/python -m pip install --upgrade pip
   /tmp/plexity_sdk_release/bin/pip install dist/plexity_sdk-<version>-py3-none-any.whl
   /tmp/plexity_sdk_release/bin/python - <<'PY'
   from plexity_sdk import GraphRAGClient, PlexityClient
   client = PlexityClient(base_url="https://example", api_key="test")
   rag = GraphRAGClient(client)
   print(rag.validate_backend_support())
   PY
   ```

   Install optional dependencies (for example `pip install httpx`) in the same environment when the import check requires them.

4. Tag the commit with `vX.Y.Z` and push the tag. The GitHub **Release** workflow:
   - Verifies the tag matches the version.
   - Rebuilds the sdist/wheel.
   - Publishes to PyPI using the `PYPI_API_TOKEN` repository secret.

Detailed instructions live in [`docs/RELEASING.md`](RELEASING.md).

## Framework Integrations

Bridge the SDK with popular retrieval frameworks using the bundled helpers:

```python
from plexity_sdk import (
    GraphRAGClient,
    LangChainRetrieverOptions,
    PlexityClient,
    create_langchain_retriever,
)

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...")
rag = GraphRAGClient(client, org_id="org_default", environment="prod")

retriever = create_langchain_retriever(
    rag,
    options=LangChainRetrieverOptions(max_entities=7, max_communities=7),
)

documents = retriever.get_relevant_documents("Where do I configure webhooks?")
```

Install integration extras as needed: `pip install plexity-sdk[langchain]`, `pip install plexity-sdk[llamaindex]`, or `pip install plexity-sdk[haystack]`. A combined `frameworks` extra installs all helpers at once.

Each factory returns a ready-to-use retriever that calls the Plexity GraphRAG endpoints under the hood while translating query options to framework-native constructs. Available helpers:

- `create_langchain_retriever` / `LangChainRetrieverOptions`
- `create_llamaindex_retriever` / `LlamaIndexRetrieverOptions`
- `create_haystack_retriever` / `HaystackRetrieverOptions`

All helpers accept optional telemetry flags so you can correlate framework usage with orchestrator executions.

## Async Transport

Install the async extra (`pip install plexity-sdk[async]`) to access the fully non-blocking `AsyncPlexityClient`:

```python
import asyncio
from plexity_sdk import AsyncPlexityClient

async def main():
    async with AsyncPlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...") as client:
        workflows = await client.list_workflows()
        print(workflows)

asyncio.run(main())
```

Every REST endpoint available on `PlexityClient` has an awaitable counterpart—`search_graphrag`, `index_graphrag`, and automation helpers included—powered by `httpx.AsyncClient`.

## Typed Models

Need structured results? Import the lightweight dataclasses provided under `plexity_sdk.models` or call the typed helpers on the clients:

```python
from plexity_sdk import PlexityClient

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...")
workflows = client.list_workflows_typed()  # -> List[WorkflowSummary]
execution = client.get_execution_typed("exec-123")  # -> ExecutionSummary
```

Async callers can `await client.list_workflows_typed()` or `await client.get_execution_typed()` for the same dataclasses.
