# Phase 9 completion — local RAG retrieval

Completed 7 October 2026 following the user's Phase 9 request and subsequent instruction to continue.

## Delivered

- Local CPU embedding pipeline using Sentence Transformers 5.7.0, PyTorch 2.14.1+cpu and the pinned Apache-2.0 all-MiniLM-L6-v2 snapshot. All required model files are prepared under the ignored local `models/` directory. No paid API, subscription or account is needed.
- Explicit preparation command and checksum manifest; request-time code loads local files only, refuses Python socket connections and disables model downloads, remote code and telemetry paths.
- Token-aware 224-token windows with 32-token overlap, exact token-ID batching, evaluation/inference mode, mean pooling and normalized 384-dimensional vectors. One bounded CPU subprocess runs at a time and exits after each operation.
- Owner-scoped indexing/status/search endpoints; exact pgvector cosine search filtered by the selected materials and current model revision; idempotent index writes, partial-index recovery and safe failure states.
- A source-search panel shared by teachers and students: preparation state, topic input, cited excerpts, similarity labels, original-page navigation and insufficient-evidence handling. No answer or MCQ is generated.
- Narrow database grant script, updated dependency locks/settings, [setup and implementation guide](rag.md), [phase plan](phase-9-plan.md), README and readiness/frontend updates.

Existing SQL migrations and immutable source chunks were preserved. Runtime source search uses the existing PostgreSQL vector tables. No LangChain layer or cloud integration was added. Generator/verifier hardware selection remains pending.

## Actual verification

| Check | Result |
|---|---|
| Full backend regression suite, database and real-model tests enabled | **122 passed**, none skipped; one existing Starlette HTTPX deprecation warning |
| Additional recovery test added after full-suite collection | **1 passed**; failed embeddings write no vectors, existing partial index fills safely |
| Distinct backend checks | **123 passed** across those two runs |
| Full frontend suite | **51 passed** across six files |
| Browser integration | **26 checks passed**, including real local embeddings → pgvector → cited source retrieval |
| TypeScript / production build | Passed |
| Ruff / Python dependency consistency | Passed |
| Visual review | Inspected desktop/mobile source-search screenshots; browser checked mobile horizontal overflow |

The actual model test covers dimension, finite unit-norm vectors, identical-text reproducibility with dropout disabled, long inputs beyond the normal 256-token truncation boundary, and one synthetic related-versus-unrelated comparison. The browser test uploaded a short synthetic PDF, indexed both passages with the real CPU model, retrieved the normalization passage and opened its original source page. SQL-specific tests use clearly identified synthetic orthogonal vectors to isolate filtering/access rules; they are never used by application runtime.

The initial model test exposed a tokenizer API compatibility issue in the installed Transformers version. The worker now builds the pinned BERT model's input tensors directly from complete token-ID windows, without a decode/re-tokenize step. Evaluation mode is explicit, and the final model regression passed. Early frontend runs also encountered a child-component mock mismatch and worker startup timeouts while other heavy checks were active. The corrected final six-file suite passed, with heavier suites run sequentially. No failing check was disabled.

## Evidence files

Paths relative to the surrounding task workspace:

- `work/phase9-backend-tests.log` — 122-test full backend run.
- `work/phase9-recovery-tests.log` — additional recovery integration test.
- `work/phase9-frontend-final.log` — 51 frontend tests.
- `work/phase9-browser-tests.log` — 26 real-browser checks.
- `work/phase9-build-final.log` — production build.
- `work/phase9-browser/rag-desktop.png` and `rag-mobile.png` — inspected rendered application, synthetic fixtures.

Screenshots and test similarities are development evidence, not reported experimental accuracy, student outcomes or MCQ-quality results. No sustained memory/latency benchmark or large-corpus evaluation was conducted. Approximately 87.3 MiB is the observed model snapshot's on-disk size, not runtime RAM usage.

## Remaining boundaries

Native PostgreSQL/pgvector installation, password authentication and real multi-connection concurrency remain unverified. Tests used the documented disposable PostgreSQL/pgvector adapter with restricted roles. No real database, application credentials, active `.env` or production upload folder was provisioned. Before native use, follow [rag.md](rag.md) and apply the new grant script as the trusted database operator.

Indexing is bounded synchronous work, not a durable background-job service. API model-file presence is a preliminary availability check; inference verifies checksums and can still fail safely. CPU/time/input bounds are not a hard memory sandbox. Large-scale throughput and multilingual relevance remain to be evaluated. The default cosine threshold is provisional; a retrieved passage is neither a verified answer nor a confidence percentage. Character-bounded excerpts are not generator-token budgeting: the later generator must use its own tokenizer, preserve the exact evidence used, and treat source instructions as untrusted data.

OCR, pasted-text ingestion, document replacement/archive UI and old-vector retention policies remain planned. No generator/verifier LLM, MCQ generation, mathematical validator, adaptive learning or evaluation results were implemented or claimed in this phase. No earlier PPT was altered to imply such results.

Next roadmap phase: **Phase 10 — generator LLM**, starting with realistic local hardware/model validation. Phase 9 work stops at retrieval.
