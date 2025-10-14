# Incremental Indexing Overview

This document describes the production infrastructure that enables document-level change detection and incremental graph indexing inside the Plexity GraphRAG stack. The goal is to eliminate mandatory full rebuilds whenever input content changes.

## Goals

- Detect when a document is new, updated, unchanged, or removed without reprocessing the entire corpus.
- Persist document version metadata (hashes, sizes, indexing status, provenance) inside PostgreSQL.
- Drive the GraphRAG ingestion pipeline so that only the documents that require work are sent to the LLM-driven orchestrator.
- Provide HTTP and programmatic APIs that expose incremental settings such as `mode`, `forceReindex`, `skipUnchanged`, and `detectDeletions`.
- Keep a complete audit trail for regulatory and debugging purposes.

## Key Components

### 1. Database Schema (`migrations/030_graphrag_document_tracking.sql`)

The migration introduces the following core structures:

| Table | Purpose |
| ----- | ------- |
| `graphrag_indexed_documents` | Stores per-document hashes, indexing metadata, status flags, and statistics. |
| `graphrag_entity_provenance` / `graphrag_relationship_provenance` | Tracks which documents produced which entities/relationships, enabling targeted invalidation. |
| `graphrag_change_logs` | Immutable audit log for creations, updates, deletions, and invalidations. |
| `graphrag_indexing_jobs` | Async job tracker for orchestrated incremental runs. |
| `graphrag_detect_changed_documents(...)` | PL/pgSQL function that compares incoming hashes against stored values and categorises documents as `new`, `updated`, or `unchanged`. |

### 2. Document Versioning Utilities (`packages/graphrag/src/utils/document-versioning.ts`)

The utility layer provides:

- SHA-256 hashing (`hashDocumentContent`) and prompt hashing (`hashExtractionPrompt`).
- `enrichDocumentsWithVersioning` to attach hash, size, schema version, and model metadata to `Document` objects.
- `detectDocumentChanges` which wraps the database function and returns a rich `ChangeDetectionResult` including the per-document diff and hash history.
- Persistence helpers (`recordDocumentIndexing`, `updateDocumentStats`, `markDocumentFailed`, `logDocumentChange`, etc.) used by the incremental services and API surface.

### 3. Incremental Indexing Service (`packages/graphrag/src/indexing/incremental.ts`)

`indexDocumentsIncremental` accepts an `IncrementalIndexingContext` { db, orchestrator, config } and an `IncrementalIndexOptions` payload. It:

1. Enriches the incoming documents with version metadata.
2. Runs change detection (if enabled) to separate `new`, `updated`, `unchanged`, and `reindexed` inputs.
3. Optionally invalidates provenance for updated documents.
4. Invokes the GraphRAG orchestrator with only the documents that require work.
5. Records indexing state and writes change log entries.
6. Returns structured stats and the list of document changes for downstream reporting.

This service is used both internally by the HTTP API and can be imported directly:

```ts
import { indexDocumentsIncremental } from '@plexity/graphrag';
import { GraphRAGOrchestrator } from '@plexity/graphrag/node-integration';
import { Pool } from 'pg';

const db = new Pool({ connectionString: process.env.DATABASE_URL });
const orchestrator = new GraphRAGOrchestrator(config);

const result = await indexDocumentsIncremental(
  { db, orchestrator, config },
  {
    mode: 'incremental',
    orgId: 'org-123',
    documents,
    detectChanges: true,
    skipUnchanged: true,
    detectDeletions: false
  }
);
```

### 4. HTTP Node Integration (`packages/graphrag/src/node-integration.ts`)

`runGraphRAGIndex` now performs the entire incremental lifecycle:

1. Normalises the request payload and loads documents from arrays, directories, files, or S3 (with optional extension filtering).
2. Delegates indexing to `indexDocumentsIncremental`.
3. Optionally marks documents as stale when they are missing from the incoming payload (`detectDeletions`).
4. Returns a rich response containing:
   - `incremental` settings that were applied.
   - `changeSummary` with document IDs grouped by change type.
   - Raw `changes` from the incremental service.
   - Per-source load counts and any duplicate IDs detected during ingestion.

The request body now supports the following incremental parameters in addition to the existing ingestion fields:

| Field | Description |
| ----- | ----------- |
| `mode` / `index_mode` | `full`, `incremental`, or `selective`. Defaults to `incremental`. |
| `forceReindex` | Ignore hashes and reindex everything. |
| `skipUnchanged` | Skip documents flagged as unchanged (default `true`). |
| `detectChanges` | Toggle hash comparison (default `true`). |
| `detectDeletions` | Mark documents that are missing from the payload as `stale`. Defaults to `true` for `mode = full`. |
| `invalidateStale` | Whether to invalidate provenance records for updated docs. |
| `schemaVersion` | Override schema version stored with each document. |
| `documentIds` | Optional list used with `mode = selective` to constrain change detection. |

Example request:

```bash
curl -X POST https://api.plexity.ai/graphrag/index \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "org-123",
    "documents": [{ "id": "doc-1", "content": "Updated body", "metadata": {"source": "crm"} }],
    "mode": "incremental",
    "detect_changes": true,
    "skip_unchanged": true,
    "detect_deletions": false
  }'
```

### 5. Test Coverage

Unit tests for the incremental service live in `packages/graphrag/tests/unit/incremental-indexing.test.ts`. They stub the Postgres pool and orchestrator in order to validate:

- New documents trigger indexing and are reported correctly.
- Unchanged documents are skipped when `skipUnchanged` is enabled.

Run the unit test suite with:

```bash
pnpm --filter @plexity/graphrag test:unit
```

### 6. Operational Notes

- **Hash collisions**: SHA-256 is used for content hashes; collisions are practically impossible for the document sizes we handle.
- **Zero-document payloads**: When `detectDeletions` is true and no documents are supplied, the service marks all previously indexed documents as stale to match the desired "clear" semantics for full rebuilds.
- **Duplicate IDs**: When duplicates are encountered during ingestion (e.g., the same ID from files and S3), the last document wins and the duplicates are surfaced in the response for visibility.
- **Extensibility**: Additional ingestion sources can plug into `loadDocumentsFromSources` by returning plain `Document` objects populated with content and metadata.

---

By combining persistent document metadata, deterministic hashing, and tight integration with the GraphRAG orchestrator, the platform can now perform fast incremental rebuilds instead of repeated full reprocessing cycles.
