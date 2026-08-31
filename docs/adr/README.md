# Architecture Decision Records

Short records of the key technical decisions behind this project — what was
decided, why, and what the consequences are. Each ADR is deliberately small;
they are a decision log, not design documents.

| ADR | Title |
|-----|-------|
| [0001](0001-no-framework-at-runtime.md) | No framework at runtime — hand-rolled RAG |
| [0002](0002-bm25-built-at-runtime.md) | BM25 keyword index built at runtime from the vector DB |
| [0003](0003-three-layer-env-loading.md) | Three-layer env loading with secrets outside the workspace |
| [0004](0004-pii-sanitization-before-indexing.md) | PII sanitization in the pipeline, never in the app |
| [0005](0005-sqlite-facts-db-prepared.md) | SQLite facts DB as a prepared building block for the SQL path |
| [0006](0006-vision-pdf-normalization.md) | Vision-based PDF normalization after failed text-layer extraction |
