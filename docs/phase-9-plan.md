# Phase 9 — local RAG pipeline

Objective: locally index authorized PDF passages and retrieve relevant, page-cited evidence for a topic. No generator/verifier model is run in this phase.

Files: backend `rag/` model preparation, offline embedding worker, service, schemas and routes; shared frontend source-search panel; runtime grants; test fixtures and setup/completion guides.

Database: reuse immutable `embedding_models` and `embeddings` with 384-dimensional normalized vectors. No migration changes. Add narrowly scoped SELECT/INSERT grants; ownership and selected-material filtering occur before ranking/limit.

API: POST `/rag/materials/{id}/index`, GET `/rag/materials/{id}`, POST `/rag/search`. Indexing is bounded synchronous work, idempotent by model revision/chunk, with atomic inserts. Search accepts 1–5 owned materials and a topic, returns page-cited excerpts or an explicit insufficient-evidence result. It never substitutes model memory or cloud search.

Dependencies: CPU-only PyTorch, Sentence Transformers, their pinned FREE / OPEN SOURCE dependencies, and the Apache-2.0 all-MiniLM-L6-v2 embedding checkpoint. Initial installation/download requires internet, no account/payment/card; runtime loads a pinned local snapshot only, disables remote code/telemetry/network access, and has no download fallback. Model files live under ignored `models/`.

Hardware: CPU, two compute threads, small batches, one embedding subprocess at a time, exit after each operation to release model memory before later LLM phases. Token-aware windows cover long Phase 8 chunks instead of silently truncating them. This embedding model does not select or validate either generator/verifier LLM.

Retrieval: exact pgvector cosine ranking over owner + explicitly selected documents + matching revision; duplicate-content suppression; configurable provisional score threshold; bounded source excerpts with page IDs/hashes. Cosine scores are similarity values, never accuracy/confidence percentages. The future generator must budget using its own tokenizer and treat source text as untrusted.

Tests: offline real-model smoke check, dimension/normalization/window coverage, pgvector ranking and owner/material isolation, missing/partial index, missing model/error paths, idempotence, context budget/provenance, UI errors/loading/search, browser integration. Record actual measured checks without making research-quality claims. Native PostgreSQL setup remains a separate documented prerequisite.
