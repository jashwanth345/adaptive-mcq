# Local source retrieval — Phase 9

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

The **Study materials** screen now prepares an uploaded PDF for semantic search and finds page-cited source passages. It uses local Sentence Transformers embeddings and exact PostgreSQL/pgvector cosine search. It does not answer the question or generate an MCQ. Teacher and student materials remain private.

## Setup on the supplied Windows laptop

The tested environment is Windows x64 with Python 3.12.14. From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m backend.prepare_embeddings
```

The first command installs the pinned dependencies. The lockfile explicitly selects the official **CPU-only Windows/Python 3.12 PyTorch wheel**, avoiding GPU/CUDA packages. For another OS/Python version, deliberately select its corresponding free CPU wheel and regenerate/test the lock; do not silently replace it with a GPU distribution. The `.in` file records CPU-only intent and assumes torch has first been installed from the official CPU index.

The second command is an explicit one-time public model download. It needs internet, but no account, credit card, API key, subscription or inference service. It downloads only the selected snapshot's configuration/tokenizer files, model card and safetensors weights. It writes per-file SHA-256 values to `models/all-MiniLM-L6-v2/snapshot.json`. If that snapshot is complete and valid, it does not download again. No application request triggers a download. Back up/copy this model directory with the local installation to run offline.

The native PostgreSQL operator must apply the new permissions to the existing database, after migrations 001–003 and the previous auth/material permission scripts:

```powershell
psql -h 127.0.0.1 -U YOUR_DATABASE_OPERATOR -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f database/rag_runtime_grants.sql
```

Replace the operator placeholder with the actual local operator account. Do not grant database ownership to the API account. No migrations were changed or added. Readiness remains a backend/auth foundation check: it does not certify model files or RAG permissions. The material search-status endpoint checks index coverage and local model-file/dependency presence; inference also verifies hashes.

Start PostgreSQL, the backend and frontend using the existing setup guides. Ollama is not required for this phase. Upload/open a PDF → **Prepare for search** → enter a topic → **Find passages** → **View source page**. The UI searches one selected document; the API supports 1–5 explicitly selected owned materials. Course membership does not imply permission to retrieve another user's private uploads.

## FREE / OPEN SOURCE components

| Component | Selected local use |
|---|---|
| Sentence Transformers 5.7.0 | FREE / OPEN SOURCE; local model execution |
| PyTorch 2.14.1+cpu | FREE / OPEN SOURCE; CPU inference |
| Transformers 5.19.0 / tokenizers | FREE / OPEN SOURCE; local model/tokenizer loading |
| all-MiniLM-L6-v2 | FREE / OPEN SOURCE; Apache-2.0 model, 384 dimensions |
| PostgreSQL + pgvector | FREE / OPEN SOURCE; exact cosine vector search |
| Direct Python/FastAPI/Pydantic | FREE / OPEN SOURCE; orchestration and contracts |

All transitive packages are pinned in the runtime lockfile. LangChain is unnecessary for this pipeline. SymPy is now installed as a PyTorch dependency; mathematical MCQ validation is still planned. There is no OPTIONAL PAID component or paid API fallback.

Model identity: `sentence-transformers/all-MiniLM-L6-v2`, pinned commit `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The vector revision also includes preprocessing/pooling identity: `token224-stride192-mean-l2-v1`. The on-disk snapshot totals approximately 87.3 MiB (including configurations/model card); this is file size, not a claim about runtime RAM. Do not edit its manifest or files manually. A future checkpoint/dimension/pipeline change requires an explicit versioned reindexing decision. Generator/verifier **Hardware-validated model selection remains pending**.

## Processing and hardware behaviour

Each index/search request runs at most one embedding subprocess. The API-wide RAG gate rejects concurrent embedding operations with a recoverable busy response. Run the supported single-worker backend launcher. The subprocess uses CPU, two compute threads, one interop thread, batches of at most four windows, evaluation mode and inference mode. It exits after each operation, releasing the model before a future generator/verifier stage. This trades repeated cold-start time for lower persistent memory use; it is not a throughput guarantee.

The worker loads only the local snapshot with `local_files_only=True`, `trust_remote_code=False` and safetensors. Offline and telemetry-disable flags are set before model-library imports; Python socket connect calls are refused in the worker. These safeguards provide no application cloud/download path; they are not an OS-level network sandbox. Snapshot hashes detect incomplete/corrupted local files. The local OS account and its installed code remain trusted.

The model normally truncates after 256 WordPiece tokens. This implementation tokenizes the full source, then embeds 224-token windows with stride 192, retaining a 32-token overlap. Each exact token-ID window is wrapped with this pinned BERT tokenizer's CLS/SEP tokens. It never decodes and re-tokenizes partial WordPieces. Window sentence vectors are averaged and L2-normalized to one 384-dimensional chunk vector. Every input token is covered; the quality of this pooling choice still needs evaluation. The same procedure embeds search queries.

Phase 8 chunks remain immutable: their old `token_count` is still a conservative UTF-8 byte estimate. Actual embedding-token lengths are computed by the worker and checked by model tests; no database field is misleadingly rewritten as generator-token output. A future generator must use **its own tokenizer**, reserve prompt/output space and include citation overhead. This phase's source-excerpt budget is measured in characters, not LLM tokens.

Limits: 500 missing chunks per index operation, 500-character query, 1–5 distinct material IDs, 180-second subprocess timeout and 210-second browser timeout for indexing/search. Prepared Phase 8 documents fall within the normal chunk cap. Timeouts kill the child and persist no partial new batch. These operational defaults are not experimentally optimized. They do not impose a hard process-memory limit. Maximum-size corpus performance and long-running workload tests remain to be evaluated on the supplied laptop.

## API and persistence

All routes require the authenticated account's current role/session. Request JSON rejects extra fields and is capped at 16 KiB. All RAG responses use `Cache-Control: no-store`.

| Route | Behaviour |
|---|---|
| GET `/api/v1/rag/materials/{id}` | Owned document's total/indexed passages, `not_indexed`/`partial`/`ready`, local-model presence and pinned revision |
| POST `/api/v1/rag/materials/{id}/index` | Index missing chunks; returns completed status synchronously |
| POST `/api/v1/rag/search` | JSON `{query, material_ids}`; returns cited excerpts or `insufficient_evidence` |

Indexing checks ownership before model work, reads only missing chunk vectors, and writes model metadata, embeddings and an audit event in one database transaction. It does not hold a database connection while the model runs. `(chunk_id,model_id)` prevents duplicate vectors; repeating a completed request is a no-op. Partial older indexes can fill their missing chunks. A failed computation writes no vectors; a failed database transaction rolls back the new batch. After an uncertain commit/lost HTTP response, refresh status or retry: existing vectors are reused. No durable queue/crash-resumable indexing job is claimed.

Vector tables remain append-only. Runtime permissions grant only SELECT and required column INSERT. Ownership is enforced by backend queries and composite foreign keys, not per-user database RLS. A model revision change isolates old vectors, rather than mixing incompatible representations. There is no automatic deletion of old vectors or material replacement feature in this phase.

Search requires every requested material to be owned, nonarchived and fully indexed for the exact current revision. Unauthorized/nonexistent IDs return 404. An incomplete index returns 409. Missing model/dependencies, inference failures, timeout and busy states have distinct recoverable UI messages. There is no alternative provider call.

## Retrieval contract and limitations

Exact cosine search filters **owner + selected materials + document version 1 + model revision + nonarchived state before ranking and LIMIT**. It retrieves at most eight times `RAG_TOP_K` candidate rows, suppresses identical content hashes, and returns up to `RAG_TOP_K` sources within `RAG_CONTEXT_CHARS`. Stable chunk-ID ordering breaks equal-score ties. Duplicate suppression or the excerpt budget can yield fewer than the requested top-k.

Defaults in `.env.example`: `RAG_TOP_K=3`, `RAG_MIN_SIMILARITY=0.25`, `RAG_CONTEXT_CHARS=2400`. The threshold is provisional and must be calibrated with relevance labels. A cosine similarity is **not a confidence score, probability, factual correctness rating or accuracy percentage**. A passage passing this filter is not yet verified as sufficient to answer a question. If no passage passes, the API returns `insufficient_evidence` with no source/answer fabrication.

Each source carries a citation ID (S1…), material/document/chunk IDs, title, original page range, original content hash, exact excerpt hash, similarity and an explicit clipping flag. The UI renders extracted text as text, never HTML. Only owned source content is returned. The source list is the handoff to later generation; no prompt or generated question is produced here. Retrieved instructions are untrusted document text, not application commands. Prompt separation, source grounding and independent verification must be enforced in later phases. Search results are ephemeral; later generation must persist the actual selected excerpt/hash with its run for reproducibility.

## Verification and boundaries

```powershell
$env:MCQ_RUN_DB_TESTS = '1'
$env:MCQ_RUN_MODEL_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -p no:cacheprovider
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

Run heavier suites sequentially on 8 GB RAM. The browser suite requires the prepared local embedding snapshot and installed Chrome/Edge. It uses actual local model inference and the real backend, with disposable PostgreSQL and temporary PDFs/accounts. Unit integration tests also use explicitly synthetic orthogonal vectors to isolate SQL ranking/access rules; those are never a production fallback. See the Phase 9 completion record for the final observed results.

Tests do not establish native PostgreSQL password authentication/concurrency, retrieval-quality metrics, full-stack LLM feasibility or learning outcomes. Native PostgreSQL/pgvector setup remains pending. Larger corpora, multilingual retrieval, reranking, persistent jobs, archival cleanup and calibrated relevance evaluation remain planned. Generator and verifier inference remain later phases.

Primary references: [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [SentenceTransformer API](https://sbert.net/docs/package_reference/sentence_transformer/model.html), [pgvector exact search and cosine distance](https://github.com/pgvector/pgvector).
