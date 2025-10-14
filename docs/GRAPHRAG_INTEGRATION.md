# GraphRAG Integration Guide

## Overview

GraphRAG (Graph Retrieval-Augmented Generation) is a comprehensive knowledge graph solution that combines traditional RAG with graph-based reasoning. This integration provides enterprise-grade capabilities for document indexing, entity extraction, relationship mapping, and intelligent querying.

## 🎯 Key Features

### Core Capabilities
- **Multi-Provider LLM Integration**: Works with OpenAI, Anthropic, Groq, and Ollama
- **Advanced Entity Extraction**: NLP-powered entity recognition with type classification
- **Relationship Mapping**: Automatic relationship detection and weight calculation
- **Community Detection**: Hierarchical clustering using Leiden/Louvain algorithms
- **Hybrid Search**: Combined global (community-based) and local (entity-based) search
- **Vector Integration**: Seamless Pinecone and Neo4j integration

### Enterprise Features
- **Cost-Aware Processing**: Budget constraints and cost optimization
- **Quality Scoring**: Multi-dimensional response quality assessment
- **Circuit Breaker Patterns**: Automatic failover and recovery
- **Performance Monitoring**: Comprehensive metrics and health checks
- **Scalable Storage**: Support for Neo4j, Pinecone, and memory backends

### SDK Helpers
- **Unified Infrastructure Clients**: `@plexity/integrations/infrastructure` now ships production-ready helpers for Neo4j, Pinecone, and LangSmith so services can connect, embed, and provision resources with consistent error handling.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 GraphRAG Orchestrator                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Document   │  │   Entity    │  │ Relationship│        │
│  │   Parser    │  │ Extractor   │  │ Extractor   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Community   │  │   Global    │  │   Local     │        │
│  │ Detector    │  │   Search    │  │   Search    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌─────────────────────────────────────┐ │
│  │  Graph Store  │  │         Vector Store              │ │
│  │   (Neo4j)     │  │        (Pinecone)                 │ │
│  └───────────────┘  └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Package Structure

```
packages/graphrag/
├── src/
│   ├── core/
│   │   └── orchestrator.ts          # Main orchestration logic
│   ├── indexing/
│   │   ├── parser.ts                # Document parsing and chunking
│   │   ├── entity-extractor.ts      # NLP entity extraction
│   │   ├── relationship-extractor.ts # Relationship detection
│   │   └── community-detector.ts    # Graph clustering algorithms
│   ├── querying/
│   │   ├── global-search.ts         # Community-based search
│   │   ├── local-search.ts          # Entity-based search
│   │   └── hybrid-search.ts         # Combined search strategies
│   ├── storage/
│   │   ├── graph-storage.ts         # Neo4j integration
│   │   └── vector-storage.ts        # Pinecone integration
│   └── types/
│       ├── index.ts                 # Core type definitions
│       ├── prompts.ts               # LLM prompt templates
│       └── errors.ts                # Error handling
└── examples/                        # Workflow examples
```

## ⚙️ Configuration

### Environment Variables

```bash
# Core GraphRAG Settings
GRAPHRAG_CHUNK_SIZE=1200
GRAPHRAG_CHUNK_OVERLAP=100
GRAPHRAG_COMMUNITY_ALGORITHM=leiden  # leiden|louvain
GRAPHRAG_MAX_COMMUNITY_SIZE=10
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
GRAPHRAG_LLM_MODEL=gpt-4o-mini

# Storage Configuration
GRAPHRAG_STORAGE_TYPE=neo4j          # neo4j|memory|json
GRAPHRAG_VECTOR_STORE=pinecone       # pinecone|memory
GRAPHRAG_OUTPUT_PATH=./graphrag_output

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=graphrag
PINECONE_NAMESPACE=graphrag-dev          # optional override; auto-managed per team/environment

# LangSmith Configuration
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_API_URL=https://api.smith.langchain.com
LANGSMITH_TRACE_WEBHOOK=                 # optional trace mirror webhook

# Query Configuration
GRAPHRAG_MAX_TOKENS=12000
GRAPHRAG_CONTEXT_WINDOW=8000
GRAPHRAG_MAX_COMMUNITIES=10
GRAPHRAG_MAX_ENTITIES=20
GRAPHRAG_MAX_RELATIONSHIPS=50
GRAPHRAG_MAP_REDUCE_MAX_TOKENS=1000
GRAPHRAG_REDUCE_MAX_TOKENS=2000

# Custom Prompts (optional)
GRAPHRAG_ENTITY_PROMPT="Your custom entity extraction prompt"
GRAPHRAG_RELATIONSHIP_PROMPT="Your custom relationship extraction prompt"
GRAPHRAG_GLOBAL_SEARCH_PROMPT="Your custom global search prompt"
GRAPHRAG_LOCAL_SEARCH_PROMPT="Your custom local search prompt"
```

### Configuration Schema

The system uses Zod schemas for configuration validation:

```typescript
const config = GraphRAGConfigSchema.parse({
  indexing: {
    chunkSize: 1200,
    chunkOverlap: 100,
    communityDetectionAlgorithm: 'leiden',
    maxCommunitySize: 10,
    embeddingModel: 'text-embedding-3-small',
    llmModel: 'gpt-4o-mini'
  },
  storage: {
    type: 'neo4j',
    neo4j: {
      uri: 'bolt://localhost:7687',
      username: 'neo4j',
      password: 'password',
      database: 'neo4j'
    },
    vectorStore: {
      type: 'pinecone',
      pinecone: {
        apiKey: 'your-key',
        environment: 'your-env',
        indexName: 'graphrag'
      }
    }
  },
  querying: {
    maxTokens: 12000,
    contextWindow: 8000,
    maxCommunities: 10
  }
});
```

### Configuration APIs

The service exposes REST endpoints (all require `portal:admin` scope) to manage tenant GraphRAG configuration:

- `GET /graphrag/configs` – list summaries for `dev`, `staging`, and `prod` including version, metadata, and whether secrets exist.
- `GET /graphrag/configs/:environment?includeSecrets=1` – fetch a specific environment configuration; pass `includeSecrets=1` to decrypt encrypted secrets.
- `PUT /graphrag/configs/:environment` – replace the configuration payload. Provide `config`, optional `metadata`, and optional `secrets` (set `null` to clear stored secrets).
- `PATCH /graphrag/configs/:environment` – merge changes into the existing configuration. Include `replaceSecrets=true` to overwrite or delete stored secrets.
- `DELETE /graphrag/configs/:environment` – remove the stored configuration when decommissioning an environment.

Configuration writes automatically increment the version counter, capture the acting user when available, and encrypt secrets using the organization’s key material.

#### Admin Console Wizard

The Plexity admin console now includes a full GraphRAG Configuration Wizard (GraphRAG → Configuration Wizard). The UI exposes per-environment tabs (`dev`, `staging`, `prod`), inline validation, and dedicated editors for:

- Indexing, storage, vector store, and querying parameters
- Microsoft GraphRAG CLI integration (workspace paths and CLI environment variables)
- Secrets, including OpenAI / Anthropic / Groq / Azure OpenAI credentials, Neo4j + Pinecone keys, and arbitrary runtime environment variables (all encrypted at rest)
- Versioned metadata stored as JSON alongside each environment

Saving from the wizard invokes the same REST API, so changes remain fully scriptable. Every view also surfaces version, author, and secret status for the active environment.

#### SDK helpers

`@plexity/sdk` and `@plexity/react-sdk` ship convenience methods/hooks for interacting with tenant configurations:

- `PlexityClient.listGraphRagConfigs()`
- `PlexityClient.getGraphRagConfig(environment, { includeSecrets })`
- `PlexityClient.setGraphRagConfig(environment, payload)`
- `PlexityClient.mergeGraphRagConfig(environment, payload)`
- `PlexityClient.clearGraphRagSecrets(environment)` / `deleteGraphRagConfig`
- React hooks `useGraphRagConfigs()` and `useGraphRagConfig(environment, { includeSecrets })`

These helpers surface the encrypted secrets by explicit opt-in and mirror the shape of the REST responses, making it straightforward to automate configuration drift detection or incorporate GraphRAG bootstrap steps into provisioning flows.

#### Runtime auto-loading

GraphRAG workflow nodes (`graphrag.index`, `graphrag.search`, `graphrag.stats`, etc.) now resolve configuration and secrets directly from the tenant store at execution time. When a step runs it automatically:

1. Determines the organization, team, and environment (from the step input or execution context)
2. Fetches the stored configuration + secrets (`includeSecrets`) via the service dependency
3. Merges them with workflow overrides and environment defaults
4. Hydrates provider environment variables (OpenAI, Anthropic, Groq, Azure OpenAI, Pinecone, Neo4j, custom runtime env) before instantiating the orchestrator

This ensures every execution reflects the latest saved configuration without hard-coding sensitive values in workflows.

## 🔧 Workflow Node Types

> **Automation:** Activating a team configuration now provisions Neo4j (database, constraints, APOC), Pinecone (index + canary namespace), and LangSmith (project, dataset, baseline evaluation run, trace hook) automatically. Inspect status via `team_infrastructure_states` or `GET /team-delegation/infrastructure/:teamId`.

### Indexing Nodes

#### `graphrag.index`
Index documents into the knowledge graph.

**Input Parameters:**
- `documents`: Array of document objects to index
- `file_paths`: Array of file paths to parse and index
- `directory_path`: Directory to scan for documents
- `recursive`: Whether to scan subdirectories (default: false)
- `supported_formats`: File extensions to process (default: ['.txt', '.md', '.json'])
- `progress_callback`: Enable progress tracking (default: false)

**Output:**
- `success`: Boolean indicating success
- `message`: Human-readable status message
- `stats`: System statistics after indexing
- `documents_processed`: Number of documents processed
- `entities_extracted`: Number of entities extracted
- `relationships_extracted`: Number of relationships found
- `communities_detected`: Number of communities created

#### `graphrag.clear`
Clear all data from the knowledge graph.

**Input Parameters:**
- `confirm`: Must be `true` to proceed (safety check)

### Query Nodes

#### `graphrag.search`
Search the knowledge graph using various strategies.

**Input Parameters:**
- `query`: Search query string (required)
- `search_type`: 'local', 'global', or 'hybrid' (default: 'hybrid')
- `max_tokens`: Maximum tokens for response
- `max_communities`: Maximum communities to consider (global search)
- `max_entities`: Maximum entities to consider (local search)

**Output:**
- `answer`: Generated response
- `search_type`: Type of search performed
- `confidence`: Confidence score (0-1)
- `sources`: Source references
- `context`: Context information used
- `metadata`: Performance metrics
- `entities`: Entities used in search
- `relationships`: Relationships used in search

### Information Nodes

#### `graphrag.stats`
Get system statistics and health information.

**Output:**
- `stats`: Current system statistics
- `health`: Health check results
- `timestamp`: Report timestamp

#### `graphrag.entities`
Retrieve entities from the knowledge graph.

**Input Parameters:**
- `query`: Optional search query
- `limit`: Maximum entities to return (default: 50)
- `entity_types`: Filter by entity types
- `include_neighbors`: Include connected entities (default: false)
- `max_hops`: Maximum relationship hops for neighbors (default: 2)

#### `graphrag.communities`
Retrieve communities from the knowledge graph.

**Input Parameters:**
- `query`: Optional search query
- `limit`: Maximum communities to return (default: 20)
- `min_size`: Minimum community size (default: 2)
- `max_size`: Maximum community size
- `level`: Filter by hierarchy level

#### `graphrag.health`
Check system health status.

**Output:**
- `healthy`: Overall health status
- `components`: Individual component status
- `timestamp`: Check timestamp

## 📥 Enterprise Ingestion Pipeline

The `BulkDocumentIngestionPipeline` enables deterministic ingestion from enterprise sources—local paths, recursive directories, Amazon S3 buckets, or pre-parsed document payloads. Obtain a pipeline instance directly from the orchestrator:

```ts
import { GraphRAGOrchestrator } from '@plexity/graphrag';

const orchestrator = new GraphRAGOrchestrator(config);
const pipeline = orchestrator.createIngestionPipeline();

await pipeline.ingest({
  type: 's3',
  bucket: 'knowledge-base',
  prefix: 'support/',
  region: 'us-east-1'
}, {
  concurrency: 6,
  batchSize: 48,
  onProgress: info => console.log(`[ingest] ${info.phase ?? 'stage'} ${info.processed}/${info.total ?? '?'}`)
});
```

Every batch runs the complete parsing → entity extraction → relationship mapping → community detection → embedding workflow with strict error handling—no heuristic fallbacks are used.

## 🔁 Real-Time Knowledge Base Sync

Use `KnowledgeBaseSyncService` for live synchronization. It emits progress events and supports filesystem watching or webhook-driven updates.

```ts
import { KnowledgeBaseSyncService } from '@plexity/graphrag';

const sync = new KnowledgeBaseSyncService(orchestrator, config.indexing);
sync.on('progress', evt => console.log('phase', evt.phase, 'processed', evt.processed));

await sync.watchDirectory('./runbooks', {
  debounceMs: 300,
  supportedExtensions: ['.md', '.pdf']
});

await sync.applyWebhookPayload(incomingDocuments);
```

## 🤝 Framework Connectors

`@plexity/integrations` now ships native adapters for LangChain, LlamaIndex, and Haystack. The adapters translate structured graph context into framework-specific document abstractions so you can plug GraphRAG into existing retrieval chains.

```ts
import { LangChainGraphRAGConnector } from '@plexity/integrations/dist/rag/langchain';

const connector = new LangChainGraphRAGConnector(orchestrator, { searchType: 'hybrid', maxEntities: 12 });
const retriever = await connector.asRetriever();
const docs = await retriever.getRelevantDocuments('Outline the launch dependencies');
```

Similar helpers are available via `createLlamaIndexRetriever` and `createHaystackRetriever`.

## 📋 Example Workflows

### 1. Document Indexing
```yaml
id: graphrag_indexing
steps:
  - id: index_documents
    type: graphrag.index
    input:
      directory_path: "/path/to/documents"
      recursive: true
      supported_formats: ['.txt', '.md', '.pdf']
    output_path: indexing_result
```

### 2. Hybrid Search
```yaml
id: graphrag_search
steps:
  - id: search_knowledge
    type: graphrag.search
    input:
      query: "What are the main trends in renewable energy?"
      search_type: "hybrid"
      max_tokens: 8000
    output_path: search_results
```

### 3. Knowledge Exploration
```yaml
id: explore_entities
steps:
  - id: get_entities
    type: graphrag.entities
    input:
      entity_types: ["ORGANIZATION", "TECHNOLOGY"]
      limit: 20
      include_neighbors: true
    output_path: entities
```

## 🔍 Search Strategies

### Global Search (Community-Based)
- Uses community summaries for broad, high-level insights
- Best for: Complex queries requiring understanding of large-scale patterns
- Faster processing, broader context
- Example: "What are the major themes in climate change research?"

### Local Search (Entity-Based)
- Uses specific entities and relationships
- Best for: Detailed, specific queries about particular entities
- More precise, focused results
- Example: "What companies does Tesla partner with for battery technology?"

### Hybrid Search (Combined)
- Combines both global and local strategies
- Best for: Complex queries requiring both breadth and depth
- Balanced approach with comprehensive results
- Example: "How do renewable energy policies affect automotive industry partnerships?"

## 📊 Performance Optimization

### Indexing Performance
1. **Chunk Size**: Optimize for your document types (1200 chars default)
2. **Batch Processing**: Process documents in batches for large datasets
3. **Parallel Processing**: Use multiple workers for entity/relationship extraction
4. **Memory Management**: Monitor RAM usage during large indexing operations

### Query Performance
1. **Search Type Selection**: Choose appropriate search strategy
2. **Token Limits**: Set reasonable token limits to control costs
3. **Context Filtering**: Use entity/community filters to focus results
4. **Caching**: Implement query result caching for common patterns

### Storage Optimization
1. **Neo4j Tuning**: Configure memory and query optimization
2. **Pinecone Index**: Optimize vector dimensions and similarity metrics
3. **Cleanup**: Regular maintenance to remove stale data
4. **Monitoring**: Track storage usage and performance metrics

## 🚨 Troubleshooting

### Common Issues

#### 1. Indexing Failures
```bash
# Check system health
curl http://localhost:8080/api/workflows/graphrag_health

# Verify storage connections
- Neo4j: Check connection string and credentials
- Pinecone: Verify API key and index name
- LLM Providers: Confirm API keys and quotas
```

#### 2. Poor Search Results
- **Low Confidence**: Increase quality thresholds or improve source data
- **Missing Context**: Check if relevant entities/communities exist
- **Performance Issues**: Optimize token limits and search parameters

#### 3. Storage Issues
- **Neo4j Connection**: Verify database is running and accessible
- **Pinecone Limits**: Check index capacity and API quotas
- **Memory Usage**: Monitor system resources during operations

### Health Monitoring
```yaml
# Regular health checks
- id: health_check
  type: graphrag.health
  input: {}

# Performance monitoring
- id: get_stats
  type: graphrag.stats
  input: {}
```

## 🔄 Maintenance

### Regular Maintenance Tasks
1. **Health Monitoring**: Daily health checks via workflows
2. **Performance Analysis**: Weekly performance reviews
3. **Data Cleanup**: Monthly cleanup of stale data
4. **Index Optimization**: Quarterly reindexing for improved performance

### Backup and Recovery
1. **Neo4j Backups**: Regular graph database backups
2. **Pinecone Snapshots**: Vector index backup procedures
3. **Configuration Backup**: Version control for configurations
4. **Disaster Recovery**: Documented recovery procedures

## 🛡️ Security Considerations

### Data Privacy
- **PII Handling**: Automatic detection and masking of sensitive data
- **Access Controls**: Role-based access to knowledge graph data
- **Audit Logging**: Comprehensive logging of all operations
- **Encryption**: Data encryption at rest and in transit

### API Security
- **Authentication**: Secure API endpoints with proper authentication
- **Rate Limiting**: Protect against abuse and DoS attacks
- **Input Validation**: Strict validation of all inputs
- **Output Sanitization**: Clean outputs to prevent injection attacks

This comprehensive GraphRAG integration provides enterprise-grade knowledge graph capabilities with seamless integration into your existing workflow orchestration system.
