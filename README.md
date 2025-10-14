
Graph RAG Orchestrator
=================================

Lightweight, reusable workflow runner and service for Agentic RAG. Ships with:

- YAML/JSON workflow DSL
- Durable executions/steps in Postgres
- BullMQ queues per node type (Redis)
- Wait/resume tokens
- Minimal Fastify HTTP API
- Hooks for LangChain, Pinecone, LangSmith
- Minimal Admin UI for executions/steps
- JS/TS & Python SDKs for integrations
- React embedding components for workflow launch/status
- Webhook signature utilities

Quick Start
-----------

1) Docker Compose

```
docker compose up --build
```

API at `http://localhost:8080`, Admin at `http://localhost:5173`.

2) Local Dev

- Copy `.env.example` to `.env` and fill values
- Set `ENCRYPTION_MASTER_KEY` (32+ chars / base64) for tenant data encryption
- Install: `npm i -g pnpm@9 && pnpm i`
- Run service: `pnpm --filter @plexity/service dev`
- Run admin: `pnpm --filter @plexity/admin dev`

SDKs & Embedding
-----------------

- JavaScript/TypeScript SDK (`@plexity/sdk`): see `docs/sdk-js.md`
- Python SDK (`plexity-sdk`): see `docs/sdk-python.md`
- React components (`@plexity/react`) for UI embedding: see `docs/react-components.md`
- Webhook validation helpers included in both SDKs

Run `pnpm sandbox:seed` to provision a local org + credentials. Full sandbox instructions live in `docs/sandbox.md`.

GraphRAG endpoints require a real organization row. The core multi-tenancy migration (`migrations/010_multi_tenancy.sql`) inserts a `slug='default'` org the first time it runs. If you are pointing at a fresh database make sure those SQL migrations have been applied before hitting `/graphrag/**`, or set `GRAPHRAG_DEFAULT_ORG_ID`/`DEFAULT_ORG_ID` in your environment to a known org id.

Migrations
----------

Run the SQL in `migrations/001_init.sql` against your Postgres instance.

GraphRAG routes require an organization row. The multi-tenancy migration (`migrations/010_multi_tenancy.sql`) creates a `slug='default'` org if one is missing; make sure that migration has been applied or set `GRAPHRAG_DEFAULT_ORG_ID`/`DEFAULT_ORG_ID` in your environment before exercising `/graphrag/**` endpoints.

Prisma mirrors the SQL schema (`prisma/schema.prisma`). When pointing at an existing database run `pnpm prisma migrate resolve --applied 000_baseline` once to mark the baseline, then `pnpm prisma generate` for typed access.

Prisma now mirrors the same schema under `prisma/schema.prisma`. Point the CLI at your database and run `pnpm prisma migrate resolve --applied 000_baseline` once to mark the baseline, then `pnpm prisma generate` for typed access.

Plexity GraphRAG Pipeline
-------------------------

- Next.js API surface lives under `apps/web` with routes for document events, retrieval, and admin recompute triggers.
- Shared ingestion utilities are published from `packages/core` (chunking, embeddings, Neo4j helpers, ranking, cache keys).
- Queue workers, graph analytics, summarisation, cleanup, and tenant-scoped rebuild jobs run from `apps/worker` (BullMQ + node-cron).
- Local infrastructure helpers (Redis + Neo4j) sit in `infra/docker-compose.yml`; copy `.env.example` and fill the Plexity-specific envs (`EMBED_MODEL`, `ADMIN_BEARER_TOKEN`, etc.).
- Start the stack with `pnpm --filter @plexity/web dev` and `pnpm --filter @plexity/worker dev` once dependencies are installed (`pnpm i`).

Production Setup
----------------

1. Provision infrastructure (Redis + Neo4j). For local testing, `docker compose -f infra/docker-compose.yml up -d` will bring up both services.
2. Apply the graph schema + vector index: `cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASS" -a "$NEO4J_URI" --file infra/neo4j/schema.cypher`. Override `EMBED_DIM` during the call if your embedding model differs from 3072 dimensions.
3. Ensure required env vars are set (`OPENAI_API_KEY`, `EMBED_MODEL`, `EMBED_DIM`, `REDIS_URL`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASS`, `ADMIN_BEARER_TOKEN`). See `.env.example` for defaults.
4. Start the API surface: `pnpm --filter @plexity/web dev` (or `next start` after `next build` for production). Ensure `PLEXITY_WEB_SESSION_SECRET` (32+ characters) is set in the web environment; the portal encrypts tenant sessions server-side and will refuse to run without it.
5. Start the worker processes independently: `pnpm --filter @plexity/worker dev` (or compile and run with Node in production). This boots BullMQ consumers and schedules hourly/daily jobs.
6. Drive ingestion via `POST /api/events/document` and retrieval via `POST /api/query`. The admin endpoint `/api/admin/recompute` can enqueue maintenance jobs when invoked with the bearer token (jobs: `hourly`, `summaries`, `cleanup`).
7. For tenant-scoped rebuilds after major entity/matching changes, call `/api/admin/recompute` with `{ "job": "rebuild", "tenantId": "<id>", "datasetId": "<id>", "topK": 25, "minScore": 0.85 }`. The worker runs a targeted similarity refresh instead of reprocessing all customers.

API
---

- POST `/executions` → `{ id, status }`
- GET `/executions` → list executions
- GET `/executions/:id` → execution row
- GET `/executions/:id/steps` → steps for an execution
- POST `/resume/:token` → resume a paused step
- GET `/health` → service health

Tenant Portal
-------------

- `POST /orgs` → self-service tenant registration; returns owner membership + seed JWT.
- `POST /auth/login` → exchange org slug + credentials for tenant-scoped JWT. The dashboard now requires this login flow—build-time API keys are blocked to prevent cross-tenant leakage. Successful logins issue short-lived JWTs stored in encrypted HTTP-only cookies.
- `GET /orgs/me` → organization metadata, quota snapshot, membership context.
- `PATCH /orgs/me/branding`, `PATCH /orgs/me/portal-settings` → configure portal theming + support links.
- `GET /orgs/me/members`, `POST /orgs/me/members/invite`, `PATCH /orgs/me/members/:id` → membership lifecycle.
- `GET|POST /api-keys` + `POST /api-keys/:id/revoke` → org API keys with per-minute/burst limits.
- `GET|POST /workflows`, `POST /workflows/:id/publish` → tenant workflow management.
- `GET /metrics`, `/stream/metrics`, `/events/:executionId` → org-scoped telemetry feeds.

The Next.js portal UI under `/portal/*` (dashboard, API keys, workflows, settings) calls these endpoints directly.

Customer Readiness
------------------

- [Customer Onboarding Guide](docs/customer-onboarding-guide.md)
- [Operations Incident Runbook](docs/ops-incident-runbook.md)
- [Support SLA & Escalation Alignment](docs/support-sla-alignment.md)
- [Final Launch Rehearsal Plan](docs/final-launch-rehearsal.md)

Workflows
---------

- Put YAML/JSON specs in `examples` or set `WORKFLOWS_DIR`
- Example: `examples/rag_ingest_answer.yaml`

Extending
---------

- Add nodes under `packages/runner/src/exec/nodes/*`
- Wire dependencies in `packages/service/src/deps.ts`
- Add more routes/UI as needed (DLQ, replayer, etc.)

License
-------

Proprietary to Plexity unless otherwise noted.
