# SDK Initiatives (Developer Layer)

This roadmap focuses on enterprise developer experiences for the Plexity SDK family and related GraphRAG tooling.

## Package Split & Versioning
- Split `GraphRAGClient` runtime profiles via `plexity_sdk.graphrag_runtime.GraphRAGPackage`.
- Feature flags surface through `enable_features` / `disable_features` and expose optional dependencies via extras (`graphrag-core`, `graphrag-enterprise`).
- Track version milestones and release notes per package channel.

## Neo4j-First APIs
- `Neo4jDriverManager` centralizes Aura/Bolt routing with pooling and connectivity checks.
- `Neo4jSchemaPlanner` + `Neo4jTransactionalBatchExecutor` deliver snapshotting, diffing, and migration execution.
- Incremental job APIs (`recommend_incremental_job_slices`, `trigger_incremental_job_slice`, and `Neo4jIncrementalJobAdvisor`) expose safe batch orchestration.

## Language Coverage
- Maintain the TypeScript SDK as the canonical implementation with first-class docs and samples.
- Release lightweight Go and Java wrappers aligned with common enterprise stacks.
- Offer a plugin entry point so existing ETL processes can call incremental ingestion without rewriting pipelines (`register_incremental_ingestion_plugin`).

## Documentation & Samples
- Publish sample pipelines that combine the SDK with the Neo4j Async Java driver and Apache Kafka connectors.
- Create reference architectures illustrating ingestion from SharePoint, Salesforce, and SAP with incremental updates.
- Expand troubleshooting guides to cover enterprise deployment patterns and Neo4j-specific tuning.

## Architecture Enhancements (Runtime & Ops)
- `orchestration` module provides pluggable schedulers (`InMemoryJobScheduler`, `TemporalJobScheduler`, `ArgoWorkflowsScheduler`) with sync/async entry points.
- Distributed incremental jobs support idempotent execution, status polling, and cancellation via `IncrementalJobSpec` handles.
- `storage` module adds adapters for S3, GCS, and MinIO plus registry helpers for isolating intermediate state in multi-tenant deployments.
- Access control, encryption, and compliance workflows ship through `AccessControlPolicy`, `EncryptionContext`, and `ComplianceDirective`.
- Backend parity checks are enforced at instantiation time: `GraphRAGClient` probes the orchestrator for enterprise and incremental job routes and surfaces actionable errors when the API surface is incomplete.
