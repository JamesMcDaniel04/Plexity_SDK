# Incremental Indexing Quickstart

Incremental indexing keeps embeddings and knowledge up to date without rebuilding your entire GraphRAG workspace. This quickstart walks through a vector-only migration flow designed for teams that want to retire Neo4j/graph storage while retaining fresh search embeddings.

## What You'll Build

- **Workflow**: `examples/vector-only-migration.yaml`
  - Snapshot current statistics for observability baselines.
  - Run an incremental indexing job that rehydrates the vector store (Pinecone in the example) and skips graph persistence.
  - Capture post-migration metrics to verify document counts, embedding totals, and storage status.
- **Trigger**: HTTP webhook (`/workflows/vector_only_migration/trigger`) seeded with the documents or document IDs to refresh.

## Prerequisites

1. Plexity Orchestrator running with an organisation configured for GraphRAG.
2. Secrets for the target vector store (e.g. `pinecone_api_key`, `pinecone_environment`). Store them with `secrets.set` or in the workflow UI.
3. (Optional) Documents ready to submit in the webhook payload, or a list of document IDs that should be reprocessed.

## Workflow Highlights

```yaml
  - id: vector_incremental_index
    type: graphrag.index
    input:
      mode: incremental
      detect_changes: "{{trigger.body.detect_changes ?? true}}"
      skip_unchanged: "{{trigger.body.skip_unchanged ?? true}}"
      documents: "{{trigger.body.documents}}"
      document_ids: "{{trigger.body.document_ids}}"
      config_overrides:
        storage:
          type: "{{trigger.body.storage_type ?? 'json'}}"
          vectorStore:
            type: "{{trigger.body.vector_store_type ?? 'pinecone'}}"
            pinecone:
              apiKey: "{{secrets.pinecone_api_key}}"
              environment: "{{secrets.pinecone_environment}}"
              indexName: "{{trigger.body.vector_index ?? 'customer-migration'}}"
        indexing:
          embeddingModel: "{{trigger.body.embedding_model ?? 'text-embedding-3-small'}}"
```

- `mode: incremental` reindexes only the documents or IDs supplied by the trigger.
- `config_overrides.storage.type: 'json'` removes the Neo4j dependency—only the vector store is written.
- Set `vector_store_type` to `memory` for local experimentation or `pinecone`/`pgvector` in production.

## Triggering the Migration

```bash
curl -X POST "https://your-orchestrator/workflows/vector_only_migration/trigger" \
  -H "Authorization: Bearer $PLEXITY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "documents": [
          {"id": "release-notes-2024-09", "content": "...", "metadata": {"category": "release_notes"}}
        ],
        "embedding_model": "text-embedding-3-large",
        "vector_store_type": "pinecone",
        "vector_index": "org-default-migration"
      }'
```

- Provide `documents` **or** `document_ids`. When both are omitted the workflow raises an error (see unit tests in `sdks/python/tests/test_graphrag_client.py`).
- Use `detect_changes=false` for forced refreshes when content hashes have not changed.

## Validating the Result

After the run, inspect the `post_stats` step or call the SDK directly:

```python
from plexity_sdk import GraphRAGClient, PlexityClient

client = PlexityClient(base_url="https://api.plexity.ai", api_key="sqk_...")
rag = GraphRAGClient(client, org_id="org_default")

stats = rag.stats()
print(stats["stats"]["storage"]["vectorStore"])  # e.g. pinecone

search = rag.search(
    "Summarise the release plan",
    search_type="global",
    use_microsoft_cli=False,
    config_overrides={
        "storage": {
            "vectorStore": {"type": "pinecone", "pinecone": {"indexName": "org-default-migration"}}
        }
    }
)
print(search["answer"])
```

Switch `use_microsoft_cli=True` to validate the same workflow against a Microsoft GraphRAG CLI runtime.

## Automation Tips

- Schedule the workflow with a cron trigger (`every 15 minutes`) or invoke it from your ingestion pipeline whenever a document changes.
- Combine with the new Python SDK wrappers (`PlexityClient.incremental_index_graphrag`) for unit or smoke tests that assert the vector store updates end-to-end.
- Record before/after snapshots in observability dashboards by forwarding the `before`/`after` payload to your metrics pipeline.
