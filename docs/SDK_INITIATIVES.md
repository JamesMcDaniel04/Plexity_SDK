# SDK Initiatives (Developer Layer)

This roadmap focuses on enterprise developer experiences for the Plexity SDK family and related GraphRAG tooling.

## Package Split & Versioning
- Split `@plexity/graphrag` into a slim core runtime and an enterprise add-on bundle.
- Introduce feature flags so Neo4j customers can install only the extensions they require.
- Publish clear semantic versioning guidance and upgrade notes covering both package tracks.

## Neo4j-First APIs
- Ship direct driver helpers tuned for Neo4j Aura and Bolt routing with built-in connection pooling and transactional batching.
- Provide schema diff tooling to snapshot the current graph schema, plan migrations, and push changes via the CLI / SDK.
- Add incremental job APIs that recommend job slices (e.g., by label, by organization) for safe, staged reprocessing.

## Language Coverage
- Maintain the TypeScript SDK as the canonical implementation with first-class docs and samples.
- Release lightweight Go and Java wrappers aligned with common enterprise stacks.
- Offer a plugin entry point so existing ETL processes can call incremental ingestion without rewriting pipelines.

## Documentation & Samples
- Publish sample pipelines that combine the SDK with the Neo4j Async Java driver and Apache Kafka connectors.
- Create reference architectures illustrating ingestion from SharePoint, Salesforce, and SAP with incremental updates.
- Expand troubleshooting guides to cover enterprise deployment patterns and Neo4j-specific tuning.
