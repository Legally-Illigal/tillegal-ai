# ADR-005: Use Supabase Postgres with pgvector for RAG Storage

- **Status:** Accepted
- **Date:** 2026-10-26
- **Decision owners:** Tillegal AI Service team

## Context

The RAG workflow needs persistent storage for legal-source chunks, embedding vectors, and metadata used to retrieve evidence. Retrieval must preserve source identity and version information so citations can be traced back to their evidence.

## Decision

Use Supabase Postgres with the `pgvector` extension as the RAG vector store. Access it through a retrieval/storage adapter and keep Supabase-specific clients and errors behind that boundary.

The application performs vector searches through a narrowly scoped PostgreSQL RPC exposed by the Supabase Data API. Direct PostgreSQL connections are reserved for schema migrations. Retrieval requests must provide explicit allowlists for document governance statuses; the adapter does not invent policy values.

Repositories are split by data responsibility (source documents, parsed structures, chunks, dense indexes, sparse indexes, and retrieval). Application use cases coordinate repository calls. The parsed structure/nodes/blocks/chunks write is one database RPC because those related rows must commit atomically.

This decision covers RAG document and vector storage. It does not select Supabase as the LangGraph checkpointer, general application database, or source of legal documents.

## Constraints

- Preserve document, source, version, and chunk identifiers with retrieved evidence.
- Keep database access out of agent and prompt modules.
- Use server-side secrets; never expose service-role credentials to clients or logs.
- Keep unit tests independent of a live Supabase project by using fakes or fixtures.
- Validate the `pgvector` schema, indexes, and retrieval behavior in integration tests.
- Keep the search RPC invoker-secure and grant execution only to the server-side `service_role`.
- Keep repository adapters focused on persistence; orchestration and cross-repository workflows belong to application use cases.

## Consequences

### Benefits

- RAG vectors and their metadata can be stored together in PostgreSQL.
- Existing PostgreSQL capabilities can support filtering and operational inspection.
- A retrieval adapter keeps the application independent of Supabase-specific APIs.

### Trade-offs

- The deployment requires a Supabase project with the required schema and `pgvector` extension.
- Retrieval quality and latency depend on embedding compatibility, indexing, and query configuration.
- Live-store integration tests require external credentials and a provisioned database.

## Revisit When

Supabase no longer meets retrieval, operational, or data-governance requirements, or an approved alternative provides a better fit.
