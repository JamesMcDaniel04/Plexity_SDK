# GraphRAG Production Setup Guide - Microsoft Mode

This guide walks you through setting up Plexity with Microsoft GraphRAG for production deployment.

## Overview

Plexity supports two GraphRAG modes:
- **Native**: Built-in entity extraction with Neo4j + Pinecone
- **Microsoft**: Leverages Microsoft's GraphRAG Python package (RECOMMENDED)

This guide covers **Microsoft GraphRAG** setup.

---

## Prerequisites

- Node.js 20+ and pnpm 9+
- Python 3.10+ with pip
- PostgreSQL database (configured via `DATABASE_URL`)
- Redis (configured via `REDIS_URL`)
- OpenAI API key (for LLM and embeddings)
- Anthropic API key (for Claude agent)

---

## Step 1: Install Microsoft GraphRAG (Python)

```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Microsoft GraphRAG
pip install graphrag

# Verify installation
graphrag --version
```

---

## Step 2: Initialize GraphRAG Workspace

```bash
# Create workspace directory
mkdir -p graphrag_workspace
cd graphrag_workspace

# Initialize GraphRAG (creates settings.yaml and prompts/)
graphrag init --root .

# This creates:
# - settings.yaml (main configuration)
# - prompts/ (customizable prompts)
# - .env (optional environment variables)
```

---

## Step 3: Configure Microsoft GraphRAG Settings

Edit `graphrag_workspace/settings.yaml`:

```yaml
encoding_model: cl100k_base
skip_workflows: []
llm:
  api_key: ${GRAPHRAG_API_KEY}  # Will use OPENAI_API_KEY from Plexity env
  type: openai_chat
  model: gpt-4o-mini
  model_supports_json: true
  max_tokens: 4000
  temperature: 0.0
  top_p: 1.0

parallelization:
  stagger: 0.3
  num_threads: 50

async_mode: threaded

embeddings:
  async_mode: threaded
  llm:
    api_key: ${GRAPHRAG_API_KEY}
    type: openai_embedding
    model: text-embedding-3-small
  vector_store:
    type: lancedb  # Or leave empty for default

chunks:
  size: 1200
  overlap: 100
  group_by_columns: [id]

input:
  type: file
  file_type: text
  base_dir: "input"
  file_encoding: utf-8
  file_pattern: ".*\\.txt$"

cache:
  type: file
  base_dir: "cache"

storage:
  type: file
  base_dir: "output"

reporting:
  type: file
  base_dir: "output/reports"

entity_extraction:
  prompt: "prompts/entity_extraction.txt"
  entity_types: [organization,person,location,event,technology]
  max_gleanings: 1

summarize_descriptions:
  prompt: "prompts/summarize_descriptions.txt"
  max_length: 500

claim_extraction:
  enabled: true
  prompt: "prompts/claim_extraction.txt"
  max_gleanings: 1

community_reports:
  prompt: "prompts/community_report.txt"
  max_length: 2000
  max_input_length: 8000

cluster_graph:
  max_cluster_size: 10

umap:
  enabled: true

snapshots:
  graphml: true
  raw_entities: true
  top_level_nodes: true

local_search:
  text_unit_prop: 0.5
  community_prop: 0.1
  conversation_history_max_turns: 5
  top_k_entities: 10
  top_k_relationships: 10
  max_tokens: 12000

global_search:
  max_tokens: 12000
  data_max_tokens: 12000
  map_max_tokens: 1000
  reduce_max_tokens: 2000
  concurrency: 32
```

---

## Step 4: Configure Plexity Environment

Update `.env` file in the project root:

```bash
# ============================================
# GraphRAG Configuration
# ============================================

# Engine Selection: 'microsoft' or 'native'
GRAPHRAG_ENGINE=microsoft

# Microsoft GraphRAG Paths
MICROSOFT_GRAPHRAG_WORKSPACE=/Users/jamesmcdaniel/Plexity_AgenticRAG_Orchestrator/graphrag_workspace
MICROSOFT_GRAPHRAG_VENV=/Users/jamesmcdaniel/Plexity_AgenticRAG_Orchestrator/venv/bin/python
MICROSOFT_GRAPHRAG_CLI=graphrag

# Microsoft GraphRAG Environment Variables (JSON format)
# These are passed to the Python subprocess
MICROSOFT_GRAPHRAG_ENV='{"GRAPHRAG_API_KEY":"${OPENAI_API_KEY}","PYTHONUNBUFFERED":"1"}'

# Default Environment for GraphRAG configs
GRAPHRAG_DEFAULT_ENVIRONMENT=prod

# ============================================
# Required API Keys (already in your .env)
# ============================================
OPENAI_API_KEY=sk-proj-...  # Already set
ANTHROPIC_API_KEY=...       # Already set (optional for Claude agent)

# ============================================
# Database & Redis (already configured)
# ============================================
DATABASE_URL=postgresql://...  # Already set
REDIS_URL=redis://localhost:6379  # Already set

# ============================================
# Security (already configured)
# ============================================
AUTH_JWT_SECRET=...           # Already set
API_KEY_SALT=...             # Already set
ENCRYPTION_MASTER_KEY=...    # Already set
```

**Important Notes:**
- Replace `/Users/jamesmcdaniel/Plexity_AgenticRAG_Orchestrator` with your actual project path
- Use absolute paths for `MICROSOFT_GRAPHRAG_WORKSPACE` and `MICROSOFT_GRAPHRAG_VENV`
- The `MICROSOFT_GRAPHRAG_ENV` JSON will pass environment variables to Python subprocess

---

## Step 5: Database Setup

Ensure GraphRAG tables exist:

```bash
# Migrations run automatically on service startup
# But verify manually:

psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%graphrag%';"

# Expected tables:
# - graphrag_configs
# - tenant_fairness_policies
# - tenant_resource_usage
# - claude_agent_sessions
# - claude_agent_tasks
# - claude_agent_logs
```

If tables are missing, migrations are in `migrations/` directory and run automatically.

---

## Step 6: Build & Start Service

```bash
# Install dependencies
npm i -g pnpm@9
pnpm i

# Build all packages
turbo run build

# Start service
pnpm --filter @plexity/service dev

# Or use Docker
docker compose up --build
```

Service should start on `http://localhost:8080`

---

## Step 7: Create Default Organization

```bash
# Create default organization (required for GraphRAG)
curl -X POST http://localhost:8080/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "default",
    "name": "Default Organization",
    "metadata": {
      "description": "Default organization for GraphRAG operations"
    }
  }'

# Response will include orgId - save this!
```

---

## Step 8: Configure GraphRAG for Organization

```bash
# Get your orgId from previous step
ORG_ID="<your-org-id>"

# Set production GraphRAG configuration
curl -X PUT "http://localhost:8080/graphrag/configs/prod" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "config": {
      "engine": "microsoft",
      "indexing": {
        "chunkSize": 1200,
        "chunkOverlap": 100,
        "embeddingModel": "text-embedding-3-small",
        "llmModel": "gpt-4o-mini"
      },
      "querying": {
        "maxTokens": 12000,
        "maxCommunities": 10,
        "maxEntities": 20
      },
      "microsoft": {
        "workspacePath": "/Users/jamesmcdaniel/Plexity_AgenticRAG_Orchestrator/graphrag_workspace"
      }
    },
    "metadata": {
      "createdBy": "admin",
      "purpose": "production-graphrag"
    }
  }'
```

---

## Step 9: Test GraphRAG Integration

### 9.1 Prepare Test Data

```bash
# Create input directory in workspace
mkdir -p graphrag_workspace/input

# Add sample document
cat > graphrag_workspace/input/sample.txt << 'EOF'
Plexity is an advanced agentic RAG orchestrator that integrates Claude AI with Microsoft GraphRAG.
It provides workflow automation, multi-tenant support, and intelligent knowledge graph management.
The system uses BullMQ for queue management, Fastify for API routing, and supports both Neo4j and Pinecone for storage.
Plexity enables organizations to build production-ready RAG applications with built-in monitoring and observability.
EOF
```

### 9.2 Index Documents

```bash
# Option A: Via Microsoft GraphRAG CLI directly (recommended for first test)
cd graphrag_workspace
source ../venv/bin/activate
GRAPHRAG_API_KEY=$OPENAI_API_KEY graphrag index --root .

# Option B: Via Plexity API
curl -X POST http://localhost:8080/graphrag/index \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "org_id": "'$ORG_ID'",
    "documents": [
      {
        "id": "doc1",
        "content": "Plexity is an advanced agentic RAG orchestrator...",
        "metadata": {"source": "test"}
      }
    ]
  }'
```

### 9.3 Query GraphRAG

```bash
# Local search (entity-focused)
curl -X POST http://localhost:8080/graphrag/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "org_id": "'$ORG_ID'",
    "query": "What is Plexity and what technologies does it use?",
    "search_type": "local",
    "max_tokens": 12000
  }'

# Global search (community-focused)
curl -X POST http://localhost:8080/graphrag/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "org_id": "'$ORG_ID'",
    "query": "What are the main capabilities of Plexity?",
    "search_type": "global"
  }'

# Hybrid search (best of both)
curl -X POST http://localhost:8080/graphrag/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "org_id": "'$ORG_ID'",
    "query": "How does Plexity integrate with Claude AI?",
    "search_type": "hybrid"
  }'
```

### 9.4 Check Stats

```bash
curl -X GET "http://localhost:8080/graphrag/stats?org_id=$ORG_ID" \
  -H "Authorization: Bearer <token>"
```

---

## Step 10: Production Deployment Checklist

### Environment Variables
- ✅ `GRAPHRAG_ENGINE=microsoft`
- ✅ `MICROSOFT_GRAPHRAG_WORKSPACE` set to absolute path
- ✅ `MICROSOFT_GRAPHRAG_VENV` points to Python interpreter
- ✅ `OPENAI_API_KEY` configured
- ✅ `DATABASE_URL` and `REDIS_URL` configured

### Infrastructure
- ✅ PostgreSQL database accessible
- ✅ Redis accessible
- ✅ Python 3.10+ with graphrag package installed
- ✅ GraphRAG workspace initialized with settings.yaml

### Service Configuration
- ✅ Default organization created
- ✅ GraphRAG config set for organization
- ✅ JWT authentication configured
- ✅ Workers enabled (`RUN_WORKERS=true`)

### Testing
- ✅ Sample document indexed successfully
- ✅ Local search returns relevant results
- ✅ Global search returns community summaries
- ✅ Stats endpoint shows correct counts

---

## Monitoring & Operations

### Health Check
```bash
curl http://localhost:8080/graphrag/health
```

### View GraphRAG Configs
```bash
curl http://localhost:8080/graphrag/configs \
  -H "Authorization: Bearer <token>"
```

### Update Configuration
```bash
curl -X PATCH http://localhost:8080/graphrag/configs/prod \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "config": {
      "querying": {
        "maxTokens": 16000
      }
    }
  }'
```

### Check Tenant Quotas
```bash
curl http://localhost:8080/monitoring/tenants/$ORG_ID/usage \
  -H "Authorization: Bearer <token>"
```

---

## Troubleshooting

### Issue: "graphrag command not found"
**Solution**: Activate virtual environment and verify installation
```bash
source venv/bin/activate
which graphrag
pip show graphrag
```

### Issue: "MICROSOFT_GRAPHRAG_WORKSPACE not found"
**Solution**: Use absolute paths in .env
```bash
# Wrong:
MICROSOFT_GRAPHRAG_WORKSPACE=./graphrag_workspace

# Right:
MICROSOFT_GRAPHRAG_WORKSPACE=/full/path/to/Plexity_AgenticRAG_Orchestrator/graphrag_workspace
```

### Issue: "OpenAI API key not found in Microsoft GraphRAG"
**Solution**: Set environment variable in MICROSOFT_GRAPHRAG_ENV
```bash
MICROSOFT_GRAPHRAG_ENV='{"GRAPHRAG_API_KEY":"'$OPENAI_API_KEY'","OPENAI_API_KEY":"'$OPENAI_API_KEY'"}'
```

### Issue: "No entities extracted"
**Solution**: Check Microsoft GraphRAG logs and settings.yaml entity types
```bash
cd graphrag_workspace
cat output/*/create_final_entities.parquet  # View extracted entities
```

---

## Performance Tuning

### Indexing Performance
Edit `graphrag_workspace/settings.yaml`:
```yaml
parallelization:
  num_threads: 100  # Increase for faster indexing
  stagger: 0.1      # Reduce delay between requests

llm:
  max_retries: 5
  request_timeout: 180.0
```

### Query Performance
```yaml
local_search:
  top_k_entities: 20        # Increase for more context
  top_k_relationships: 20
  max_tokens: 16000         # Increase for longer answers

global_search:
  concurrency: 64           # Parallel community processing
  map_max_tokens: 2000      # Larger map summaries
```

---

## Security Considerations

1. **API Key Protection**: Store in environment variables, never commit to git
2. **JWT Tokens**: Rotate `AUTH_JWT_SECRET` regularly
3. **Encryption**: GraphRAG configs with secrets are encrypted in database
4. **Rate Limiting**: Tenant fairness enforces per-org rate limits
5. **Quotas**: Configure max entities/relationships per tenant

---

## Next Steps

1. **Scale Up**: Add more documents to `graphrag_workspace/input/`
2. **Customize Prompts**: Edit files in `graphrag_workspace/prompts/`
3. **Monitor**: Use Admin UI at `http://localhost:5173` to view metrics
4. **Integrate**: Use Claude Agent service for automated integration planning
5. **Optimize**: Tune chunk sizes and entity types based on your domain

---

## Support

- **Documentation**: `/docs` directory
- **API Reference**: `http://localhost:8080/documentation` (if enabled)
- **Logs**: Check service logs for detailed error messages
- **Microsoft GraphRAG Docs**: https://github.com/microsoft/graphrag

---

**You're now running Microsoft GraphRAG in production mode!** 🚀
