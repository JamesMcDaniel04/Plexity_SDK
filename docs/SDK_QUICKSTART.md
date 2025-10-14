# GraphRAG SDK Quickstart

> Install, configure, and run the Plexity GraphRAG SDK in minutes. This guide walks you from first-time setup through production hardening, including storage adapters, LLM providers, observability hooks, and deployment patterns.

---

## 1. Audience & Prerequisites

- **Audience:** JavaScript/TypeScript developers building retrieval-augmented experiences, knowledge graph pipelines, or autonomous workflow engines.
- **Prerequisites:**
  - Node.js 20 or newer
  - pnpm 9.15 or newer (npm/yarn supported where noted)
  - A modern LLM API key (OpenAI or Anthropic). Mock providers are included for testability.
  - Optional: Docker (for running Postgres + pgvector, Neo4j, or Pinecone Local)

> **Tip:** All shell commands assume macOS/Linux. On Windows PowerShell, replace environment variable exports with `$Env:VAR="value"`.

---

## 2. Installation Matrix

| Goal | Command | Notes |
| --- | --- | --- |
| Install via pnpm | `pnpm add @plexity/graphrag-core` | Recommended when working inside a pnpm workspace |
| Install via npm | `npm install @plexity/graphrag-core` | Generates `package-lock.json` |
| Install via yarn | `yarn add @plexity/graphrag-core` | Works with Yarn v1+ |
| Install nightly tarball | `pnpm add ./dist/plexity-graphrag-core-X.Y.Z.tgz` | Useful for pre-release smoke tests |

The package ships with full TypeScript declarations, `exports` map, CJS interoperability, and tree-shakeable modules for modern bundlers.

---

## 3. First Run Checklist

1. **Bootstrap project**
   ```bash
   mkdir graphrag-starter && cd graphrag-starter
   pnpm init
   pnpm add @plexity/graphrag-core dotenv
   ```
2. **Create `.env`**
   ```bash
   cat <<'ENV' > .env
   OPENAI_API_KEY=sk-your-openai-key
   # Optional fallbacks:
   ANTHROPIC_API_KEY=
   GRAPH_NAMESPACE=quickstart
   GRAPH_SCHEMA=public
   ENV``
3. **Commit baseline** (recommended)
   ```bash
   git init
   git add package.json pnpm-lock.yaml .env
   git commit -m "chore: bootstrap quickstart"
   ```
4. **Create entry point** (see Section 4). Run with `pnpm exec tsx index.ts` or `node dist/index.js` after compiling.

---

## 4. Zero-Config Example (Memory Storage)

```typescript
import 'dotenv/config';
import { GraphRAG } from '@plexity/graphrag-core';

async function main() {
  const rag = new GraphRAG();
  await rag.initialize();

  await rag.indexDocuments([
    { id: 'doc-1', content: 'GraphRAG combines knowledge graphs with RAG.' },
    { id: 'doc-2', content: 'Entities and relationships are extracted by LLMs.' }
  ]);

  const answer = await rag.search('What does GraphRAG do?');
  console.log(JSON.stringify(answer, null, 2));

  await rag.close();
}

main().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
```

- When `OPENAI_API_KEY` is set, the default OpenAI provider boots automatically.
- Without keys, supply a mock `llmProvider` (see Section 10) to keep tests self-contained.
- Memory storage is volatile—restart the process to reset the graph.

---

## 5. File Storage Workflow

Persistent, file-backed storage is ideal for prototypes that need restart durability without external databases.

```typescript
import { GraphRAG, FileGraphStorage, FileVectorStorage, FileDocumentStorage } from '@plexity/graphrag-core';
import path from 'node:path';

const projectRoot = process.cwd();

const rag = new GraphRAG({
  dependencies: {
    storage: {
      graph: new FileGraphStorage({ basePath: path.join(projectRoot, 'data/graph') }),
      vector: new FileVectorStorage({ basePath: path.join(projectRoot, 'data/vectors') }),
      document: new FileDocumentStorage({ basePath: path.join(projectRoot, 'data/documents') })
    }
  }
});
```

- Filenames are deterministic: `data/graph/entities/<id>.json`, etc. Easy to inspect.
- Supports concurrent writes with advisory file locks.
- Use `rag.clear()` to empty all files.

---

## 6. PostgreSQL + pgvector (Production Grade)

### 6.1. Provision Database

```bash
# Launch Postgres + pgvector using Docker Compose
cat <<'YML' > docker-compose.yaml
version: '3.9'
services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: graphrag
      POSTGRES_PASSWORD: graphrag
      POSTGRES_DB: graphrag
    ports:
      - 5432:5432
YML

docker compose up -d
```

### 6.2. Configure SDK

```typescript
import { GraphRAG } from '@plexity/graphrag-core';

const rag = new GraphRAG({
  storage: {
    namespace: process.env.GRAPH_NAMESPACE ?? 'default',
    schema: process.env.GRAPH_SCHEMA ?? 'public',
    graph: {
      type: 'postgres',
      connectionString: process.env.POSTGRES_URL ?? 'postgres://graphrag:graphrag@localhost:5432/graphrag'
    },
    vector: {
      type: 'postgres',
      connectionString: process.env.POSTGRES_URL ?? 'postgres://graphrag:graphrag@localhost:5432/graphrag',
      dimensions: 1536,
      metric: 'cosine',
      index: { type: 'ivfflat', lists: 100 }
    },
    document: {
      type: 'postgres',
      connectionString: process.env.POSTGRES_URL ?? 'postgres://graphrag:graphrag@localhost:5432/graphrag',
      chunkVectorDimensions: 1536
    }
  }
});
```

### 6.3. Auto-Migrations

First `rag.initialize()` run automatically:

- Creates schema (optional) and tables for documents, entities, relationships, communities, vectors, chunks.
- Enables `pgvector` extension (`CREATE EXTENSION IF NOT EXISTS vector`).
- Applies GIN indexes for JSONB metadata + full-text search.
- Registers namespace + multi-tenant columns.

### 6.4. Production Hardening Tips

- Configure connection pool via `storage.vector.pool = new Pool({ connectionString, max: 20 })`.
- Use dedicated schema per tenant to isolate graph data.
- Pair with logical replication or change data capture for analytics.
- Backup vector tables with `pg_dump --schema-only` (struct) and `COPY` (data) for faster restore.

---

## 7. Neo4j Adapter (Graph Native)

> Neo4j support requires the optional `neo4j-driver` peer dependency.

```typescript
import { GraphRAG, Neo4jGraphStorage } from '@plexity/graphrag-core';

const rag = new GraphRAG({
  graphStorage: new Neo4jGraphStorage({
    uri: 'bolt://localhost:7687',
    username: 'neo4j',
    password: 'password'
  })
});
```

- Leverages Cypher queries for community detection and traversals.
- Useful when you need built-in graph algorithms or Bloom visualization.
- Combine with Postgres vector storage for hybrid search (GraphRAG supports mixing adapters).

---

## 8. Pinecone Vector Storage

```typescript
import { PineconeVectorStorage } from '@plexity/graphrag-core/storage/pinecone-storage';

const vectorStorage = new PineconeVectorStorage({
  apiKey: process.env.PINECONE_API_KEY!,
  indexName: 'graphrag-vectors',
  namespace: 'demo',
  dimension: 1536
});
```

- Dynamically imports the Pinecone SDK to keep core dependency tree slim.
- Supports hybrid dense+sparse search (`hybridSearch` helper).
- Metadata filtering uses Pinecone server-side filters.

---

## 9. Choosing an LLM Provider

### 9.1. OpenAI (Default)

```typescript
import { GraphRAG, OpenAIProvider } from '@plexity/graphrag-core';

const rag = new GraphRAG({
  llmProvider: new OpenAIProvider({
    apiKey: process.env.OPENAI_API_KEY!,
    defaultModel: 'gpt-4o-mini',
    defaultEmbeddingModel: 'text-embedding-3-small'
  })
});
```

### 9.2. Anthropic

```typescript
import { AnthropicProvider } from '@plexity/graphrag-core';

const rag = new GraphRAG({
  llmProvider: new AnthropicProvider({
    apiKey: process.env.ANTHROPIC_API_KEY!,
    defaultModel: 'claude-3-haiku-20240307'
  })
});
```

### 9.3. LangChain Bridge

The LangChain provider lets you reuse existing tools and chains.

```typescript
import { LangChainProvider } from '@plexity/graphrag-core/providers/langchain';
import { ChatOpenAI } from '@langchain/openai';

const rag = new GraphRAG({
  llmProvider: new LangChainProvider({
    chatModel: new ChatOpenAI({
      modelName: 'gpt-4o-mini',
      openAIApiKey: process.env.OPENAI_API_KEY
    })
  })
});
```

### 9.4. Mock Provider (Testing)

```typescript
import type {
  LLMProvider,
  LLMRequest,
  LLMResponse,
  EmbeddingRequest,
  EmbeddingResponse
} from '@plexity/graphrag-core';

class MockLLM implements LLMProvider {
  async generateText(request: LLMRequest): Promise<LLMResponse> {
    return {
      text: JSON.stringify({
        entities: [{ name: 'Mock', type: 'CONCEPT', description: request.prompt.slice(0, 32) }],
        relationships: []
      }),
      model: 'mock',
      tokensUsed: { prompt: 1, completion: 1, total: 2 },
      finishReason: 'stop'
    };
  }

  async generateEmbeddings(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    return {
      embeddings: request.texts.map(() => Array(5).fill(0.1)),
      model: 'mock-embedding',
      tokensUsed: 0,
      dimensions: 5
    };
  }

  getName(): string {
    return 'mock';
  }

  getSupportedModels(): string[] {
    return ['mock'];
  }
}
```

Use `new GraphRAG({ llmProvider: new MockLLM() })` when running deterministic unit tests.

---

## 10. Observability & Telemetry

GraphRAG ships with a no-op provider; replace it with console logging, OpenTelemetry, or your platform of choice.

```typescript
import { GraphRAG, ConsoleObservabilityProvider } from '@plexity/graphrag-core';

const rag = new GraphRAG({
  observability: new ConsoleObservabilityProvider({ prefix: '[graphrag]' })
});
```

Events emitted:

| Event | When | Payload |
| --- | --- | --- |
| `indexing` | Initialization, document ingestion, chunking | Duration, counts |
| `search` | Each query | Model info, latency, citations |
| `error` | Any caught exception | message, stack |
| `fairness` | When fairness policies reserve/release quotas | delta, tenant context |

Integrate with OTEL by implementing the `ObservabilityProvider` interface and forwarding events to a tracer.

---

## 11. Tenant Fairness Policies

Prevent noisy neighbours with quota-aware policies.

```typescript
import { GraphRAG, NoOpTenantFairnessPolicy } from '@plexity/graphrag-core';

class CappedPolicy extends NoOpTenantFairnessPolicy {
  constructor(private remaining: number) { super(); }

  async reserve(delta: Record<string, number>) {
    const requested = delta.entities ?? 0;
    if (requested > this.remaining) {
      throw new Error('Entity quota exceeded for tenant');
    }
    this.remaining -= requested;
    return super.reserve(delta);
  }
}

const rag = new GraphRAG({
  fairness: new CappedPolicy(1_000)
});
```

Set tenant context per request:

```typescript
rag.setTenantContext({
  orgId: 'tenant-123',
  projectId: 'marketing-graph',
  userId: 'analyst@tenant.com'
});
```

---

## 12. Advanced Pipeline Example

```typescript
import {
  GraphRAG,
  PostgresGraphStorage,
  PostgresVectorStorage,
  PostgresDocumentStorage,
  ConsoleObservabilityProvider
} from '@plexity/graphrag-core';
import { Pool } from 'pg';

const pool = new Pool({ connectionString: process.env.POSTGRES_URL });

const rag = new GraphRAG({
  llmProvider: new MockLLM(),
  dependencies: {
    storage: {
      graph: new PostgresGraphStorage({ pool, namespace: 'prod', schema: 'graphrag' }),
      vector: new PostgresVectorStorage({ pool, namespace: 'prod', schema: 'graphrag', dimensions: 1536 }),
      document: new PostgresDocumentStorage({ pool, namespace: 'prod', schema: 'graphrag', chunkVectorDimensions: 1536 })
    },
    observability: new ConsoleObservabilityProvider()
  }
});

await rag.initialize();
await rag.indexDocuments(loadS3Documents());
const result = await rag.search('Summarize knowledge gaps for Q4');
await rag.close();
```

This pattern is production-ready: dependency injection enables connection reuse, metrics, and deterministic testing.

---

## 13. Storage Adapter Reference

| Adapter | Module | Persistence | Notes |
| --- | --- | --- | --- |
| Memory | `@plexity/graphrag-core/storage/memory-storage` | No | Fast, ideal for tests |
| File | `@plexity/graphrag-core/storage/file-storage` | Yes (local disk) | JSON/JSONL serialization |
| PostgreSQL | `@plexity/graphrag-core/storage/postgres-storage` | Yes | pgvector, namespaces, migrations |
| Neo4j | `@plexity/graphrag-core/storage/neo4j-storage` | Yes | Graph-native operations |
| Pinecone | `@plexity/graphrag-core/storage/pinecone-storage` | Cloud | Requires Pinecone index |

> **Extensibility:** Implement `GraphStorage`, `VectorStorage`, or `DocumentStorage` interfaces to plug in MongoDB, DynamoDB, Redis, etc. Export them under `storage/custom` for reuse.

---

## 14. Managing Migrations

- PostgreSQL adapter auto-creates tables but you can manage migrations yourself via SQL migrations or Prisma.
- For schema changes, bump namespace or use `ALTER TABLE ADD COLUMN` followed by `rag.clear()` or targeted updates.
- Track schema versions using `document.schemaVersion` and `entity.extractedAt` to support incremental re-indexing.

---

## 15. End-to-End Testing Strategy

- Use the bundled `MockLLM` (Section 9.4) to avoid hitting real LLMs.
- The repository includes `src/__tests__/e2e/postgres-storage.e2e.test.ts` powered by Testcontainers + pgvector for integration coverage.
- Add `vitest` config overrides:
  ```jsonc
  {
    "test": {
      "testTimeout": 120000,
      "hookTimeout": 120000,
      "env": {
        "OPENAI_API_KEY": "test",
        "POSTGRES_URL": "postgres://..."
      }
    }
  }
  ```
- To skip dockerized tests in CI, export `SKIP_POSTGRES_TESTS=1` and guard them via `if (process.env.SKIP_POSTGRES_TESTS) test.skip(...)`.

---

## 16. Packaging & Publishing

1. Build artifacts
   ```bash
   pnpm --filter @plexity/graphrag-core run build
   ```
2. Run unit + integration suites (supply API keys or mocks)
   ```bash
   pnpm --filter @plexity/graphrag-core run test:unit
   pnpm --filter @plexity/graphrag-core run test:e2e
   ```
3. Verify release metadata
   - `package.json` has `publishConfig.access=public`
   - `files` array restricts tarball to `dist`, `README`, `LICENSE`
   - Peer dependencies are optional
4. Publish
   ```bash
   cd packages/graphrag-core
   npm publish --tag beta --access public
   ```
5. Validate installation from npm
   ```bash
   mkdir /tmp/graphrag-verify && cd /tmp/graphrag-verify
   pnpm init
   pnpm add @plexity/graphrag-core@beta
   pnpm exec tsx -e "console.log(require('@plexity/graphrag-core'))"
   ```

---

## 17. Environment Variables Cheat Sheet

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Auto-initialize OpenAI provider | Required for production |
| `OPENAI_BASE_URL` | Custom endpoint / gateway | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic provider | Optional |
| `GRAPH_NAMESPACE` | Logical tenant bucket | `default` |
| `GRAPH_SCHEMA` | Postgres schema | `public` |
| `POSTGRES_URL` | Database connection string | `postgres://...` |
| `PINECONE_API_KEY` | Pinecone vector storage | -- |
| `PINECONE_ENVIRONMENT` | Pinecone environment | -- |
| `LOG_LEVEL` | Custom logging toggles | `info` |

---

## 18. Troubleshooting Guide

### Missing LLM Provider
- **Symptom:** `GraphRAG requires an LLM provider`.
- **Fix:** Supply `llmProvider`, set `OPENAI_API_KEY`, or inject `MockLLM` for tests.

### pgvector Errors
- **Symptom:** `operator does not exist: integer - vector`.
- **Fix:** Ensure `CREATE EXTENSION vector` ran; confirm `embedding` columns use the vector type and queries cast parameters (`::vector(dim)`).

### File Storage Path Errors
- **Symptom:** `TypeError: The "path" argument must be of type string`.
- **Fix:** Pass `basePath` (not `directory`) to file storage constructors. The adapters expect `FileStorageConfig` shape.

### Docker Testcontainers Timeouts
- Increase Vitest `testTimeout` to 120s.
- Ensure Docker Desktop is running and the user has permission to create containers.

### Neo4j Authentication Failures
- Verify `bolt://` URI, credentials, and DB name (`database` option). Check `neo4j.conf` for custom settings.

---

## 19. FAQ

1. **Can I use different storage adapters simultaneously?** Yes. Mix Postgres (graph documents) with Pinecone (vectors) and S3-backed document storage by providing custom adapters.
2. **Is multi-tenant isolation supported?** Namespaces enforce per-tenant partitioning across all Postgres tables and vector indexes.
3. **How do I customize chunking?** Override `config.chunkSize`/`chunkOverlap`, or subclass `GraphRAG` and override `chunkDocument`.
4. **What about streaming responses?** Implement `LLMProvider.generateTextStream` (optional) and supply streaming callbacks to `GraphRAG.search`.
5. **Does GraphRAG support incremental re-indexing?** Yes—`document.contentHash`, `document.schemaVersion`, and provenance tables allow selective refresh.

---

## 20. Next Steps

- Explore the [Install & Run in 5 Minutes](./INSTALL_AND_RUN.md) guide for a fast on-boarding walkthrough.
- Review `docs/SDK_TRANSFORMATION_ROADMAP.md` for long-term architecture decisions.
- Contribute adapters: fork the repository and add `src/storage/<adapter>-storage.ts`, then register exports in `storage/index.ts`.
- Join the community Slack (internal Plexity) for architecture office hours.

---

## Appendix A: Example Vitest Config Override

```ts
// vitest.config.compose.ts
import baseConfig from './vitest.config';
import { defineConfig, mergeConfig } from 'vitest/config';

export default mergeConfig(baseConfig, defineConfig({
  test: {
    testTimeout: 120_000,
    hookTimeout: 120_000,
    env: {
      OPENAI_API_KEY: process.env.OPENAI_API_KEY ?? 'mock-key',
      POSTGRES_URL: process.env.POSTGRES_URL ?? 'postgres://graphrag:graphrag@localhost:5432/graphrag'
    }
  }
}));
```

## Appendix B: Custom Storage Adapter Skeleton

```typescript
import type { GraphStorage, Entity, Relationship, Community } from '@plexity/graphrag-core';

export class DynamoGraphStorage implements GraphStorage {
  constructor(private readonly tableName: string) {}

  async initialize(): Promise<void> {
    // create tables / indexes
  }

  async saveEntity(entity: Entity): Promise<void> {
    // putItem to DynamoDB
  }

  // implement other GraphStorage methods...
}
```

## Appendix C: Lifecycle Hooks Reference

| Method | Typical Use | Should I await? |
| --- | --- | --- |
| `initialize()` | Create connections, ensure tables | Yes |
| `indexDocuments()` | Main ingestion pipeline | Yes |
| `search()` | Query knowledge graph | Yes |
| `clear()` | Purge storage | Yes |
| `close()` | Dispose resources | Yes |

## Appendix D: Cost Management Tips

- Use `rag.setTenantContext({ plan: 'trial', remainingTokens: 1_000 })` to track per-tenant consumption.
- Combine with fairness policies to enforce quotas.
- Enable observability provider to record token usage per search/index operation.

## Appendix E: Upgrade Path

1. **0.x to 1.0**
   - Stabilize storage adapter interfaces.
   - Introduce migration scaffolding for Postgres.
   - Finalize telemetry schema.
2. **1.x future**
   - Add multi-LLM orchestration
   - Provide GraphQL API wrapper
   - Integrate prompt optimization toolkit (see GAP #12)

## Appendix F: Glossary

| Term | Definition |
| --- | --- |
| GraphRAG | Retrieval-augmented generation system plus knowledge graph storage |
| Namespace | Logical tenant boundary in storage adapters |
| Community | Cluster of entities with high relationship density |
| Vector Storage | Embedding persistence layer used for semantic search |
| Fairness Policy | Rate limiter / quota guard for multi-tenant safety |

## Appendix G: Useful Scripts

```jsonc
{
  "scripts": {
    "dev:quickstart": "node --env-file=.env index.js",
    "test:e2e:postgres": "vitest run src/__tests__/e2e/postgres-storage.e2e.test.ts",
    "lint:types": "tsc --noEmit"
  }
}
```

## Appendix H: Support Channels

- **Slack:** `#graphrag-sdk` (internal Plexity)
- **Email:** support@plexity.ai
- **Status:** https://status.plexity.ai
- **Runbook:** See `docs/GRAPHRAG_ALERTING_RUNBOOK.md`

---

_End of Quickstart. Continue with the install-and-run tutorial for a narrative walkthrough._
