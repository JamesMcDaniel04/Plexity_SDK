# Install and Run in 5 Minutes

Follow this guided script to experience GraphRAG end-to-end from a clean machine.

## 1. Prep the Environment (30 seconds)

```bash
mkdir graphrag-demo && cd graphrag-demo
pnpm init
pnpm add @plexity/graphrag-core tsx dotenv
```

Optional: create a virtualenv for Python-based ETL steps (not required for the JS SDK).

## 2. Configure Secrets (60 seconds)

```bash
cat <<'ENV' > .env
OPENAI_API_KEY=sk-your-key
POSTGRES_URL=postgres://graphrag:graphrag@localhost:5432/graphrag
ENV
```

> **Note:** Skip `POSTGRES_URL` if you are evaluating in memory mode. Add `GRAPH_NAMESPACE` to scope tenants.

## 3. Launch Databases (Optional, 90 seconds)

```bash
cat <<'YML' > docker-compose.yaml
version: '3.9'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: graphrag
      POSTGRES_PASSWORD: graphrag
      POSTGRES_DB: graphrag
    ports:
      - 5432:5432
YML

docker compose up -d postgres
```

Check connectivity:
```bash
pg_isready -h localhost -p 5432 -U graphrag
```

## 4. Create `index.ts` (120 seconds)

```typescript
import 'dotenv/config';
import {
  GraphRAG,
  PostgresGraphStorage,
  PostgresVectorStorage,
  PostgresDocumentStorage
} from '@plexity/graphrag-core';
import { Pool } from 'pg';

async function main() {
  const pool = new Pool({ connectionString: process.env.POSTGRES_URL });

  const rag = new GraphRAG({
    storage: {
      namespace: 'demo',
      schema: 'graphrag',
      graph: { type: 'postgres', pool },
      vector: { type: 'postgres', pool, dimensions: 1536 },
      document: { type: 'postgres', pool, chunkVectorDimensions: 1536 }
    }
  });

  await rag.initialize();

  await rag.indexDocuments([
    { id: 'doc-1', content: 'GraphRAG builds knowledge graphs from documents.' },
    { id: 'doc-2', content: 'Entities and relationships are extracted by LLMs.' }
  ]);

  const result = await rag.search('Summarize GraphRAG');
  console.log(JSON.stringify(result, null, 2));

  await rag.close();
  await pool.end();
}

main().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
```

## 5. Run the Example (30 seconds)

```bash
pnpm exec tsx index.ts
```

Expected output (truncated):
```
{
  "answer": "GraphRAG combines knowledge graphs with retrieval-augmented generation...",
  "entities": [...],
  "relationships": [...],
  "tokensUsed": 123,
  "duration": 812
}
```

## 6. Verify Persisted Data (60 seconds)

```bash
psql "$POSTGRES_URL" <<'SQL'
\dt graphrag.*
SELECT id, name, type FROM graphrag.graphrag_entities;
SELECT id, source, target, type FROM graphrag.graphrag_relationships;
SELECT id, namespace FROM graphrag.graphrag_vectors LIMIT 5;
SQL
```

## 7. Switch to Memory Mode (Optional)

```typescript
const rag = new GraphRAG({
  dependencies: {
    storage: {
      graph: new MemoryGraphStorage(),
      vector: new MemoryVectorStorage(),
      document: new MemoryDocumentStorage()
    }
  }
});
```

Run again—no external services needed.

## 8. Clean Up (30 seconds)

```bash
docker compose down --volumes
rm -rf data node_modules
```

Congratulations! You installed and ran GraphRAG in under five minutes. Continue with `docs/SDK_QUICKSTART.md` for deep dives.
