# Private advisory review — Phase 11

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

## Use the website without an LLM

Open **Draft studio**, create or reopen your own saved draft, and scroll to **Verification workspace**. Select **Run test review**. The report checks question format and the integrity of the recorded source quotation, excerpt and hashes. It explicitly marks AI quality **Not evaluated** and publication **Not approved**. Reopen the draft to view saved reports; older reports are paginated. Teacher and student accounts use the same private workflow.

This default path invokes neither Ollama nor embeddings. It never changes the question, approves it, publishes it or assigns a score. Source integrity establishes that the recorded evidence matches the original owned chunk; it does not establish that the proposed answer is correct or the explanation follows from the source. Test outputs are excluded from future research evaluation and real-AI review.

## Local setup

Use the existing local database/backend/frontend setup. Native PostgreSQL with pgvector remains a deployment prerequisite; disposable test databases are not a persistent application fallback. As the trusted migration owner, apply the migration runner's current plan, which now includes **004_verifier_reports.sql**:

```powershell
.\.venv\Scripts\python.exe database/migrate.py plan
.\.venv\Scripts\python.exe database/migrate.py apply --psql 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --host 127.0.0.1 --port 5432 --database adaptive_mcq --user adaptive_mcq_migrator
```

After the existing Phase 4–10 runtime grants, apply this additive script using the trusted database-owner login:

```powershell
psql -h 127.0.0.1 -U <database-owner> -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f database/verifier_runtime_grants.sql
```

The application receives SELECT and constrained INSERT rights on advisory reports, without UPDATE/DELETE or release-gate verification/publication rights. Ownership is enforced by the backend using the authenticated account; this is not per-user database row-level security. Browser clients must never receive database credentials. No retained database was migrated during this phase.

Keep private database/JWT configuration and these application settings:

```dotenv
GENERATOR_MODE=mock
VERIFIER_MODE=mock
GENERATOR_MODEL=qwen2.5:0.5b-instruct-q4_K_M
VERIFIER_MODEL=qwen2.5:0.5b-instruct-q4_K_M
MODEL_SELECTION_STATUS=pending_hardware_validation
LLM_CONTEXT_TOKENS=2048
LLM_OUTPUT_TOKENS=512
```

**Hardware-validated model selection: pending.** The model names are unvalidated adapter candidates, not installed weights. The verifier candidate replaces the older SmolLM2 placeholder because the current bounded transport/tokenizer supports only the small Qwen tag. Using it for both roles is **same-checkpoint role separation**, not independent-model verification. Selecting a genuinely different model requires compatible tokenizer/transport support and separate hardware/quality validation. No LLM download or inference is needed for the test workflow. Do not enable real inference automatically on this 8 GB laptop.

Start the database, backend (`python -m backend.app`) and frontend (`npm.cmd --prefix frontend run dev`) using the existing guides. Run one backend worker. This phase does not start Ollama or create production credentials.

## Three verifier modes

| Mode | Behavior |
|---|---|
| `mock` — default | Deterministic format/source checks; recommendation always `NOT_EVALUATED`, `ai_executed=false`; no model calls |
| `disabled` | Saved private reports remain readable; creation disabled |
| `ollama` — explicit future use | Conceptual, AI-generated drafts only; sequential blind answer and critique; hardware/model checks required |

Modes are server settings. The request cannot choose a model, owner, verdict or approval flag. A mock-generated draft is rejected by real-AI mode before inference; the database also enforces AI-generation provenance for AI reports. No automatic API fallback, model pull, installation or cloud call exists.

## Local verifier adapter — inference not yet validated

1. Load the owner's immutable, unreleased generated draft and exact source excerpt.
2. Validate its schema and compare recorded quotation/excerpt/hash evidence with its owned original chunk. Failure prevents inference.
3. Build a **blind-answer prompt** containing the stem, options and source, without the proposed answer key or explanation.
4. Parse a strict answerability/selected-option/quotation/reason response. An answerable response must quote the exact supplied excerpt.
5. Make a second, sequential **critique call**, now including the proposed key, explanation and requested difficulty. Require categorical judgments for factual correctness, clarity, distractors, explanation and difficulty.
6. Reject model-digest changes between calls. Derive the advisory recommendation on the server and save the completed report atomically.

| Recommendation | Rule |
|---|---|
| `REJECT` | Question not uniquely answerable, factual correctness flagged as an issue, or deterministic format/source check failed |
| `PASS` | Blind answer agrees with proposed key and all five critique judgments are acceptable |
| `REGENERATE` | Answer disagreement, uncertainty or another critique issue |

These are **advisory rules**, not experimentally calibrated correctness guarantees. `REGENERATE` does not automatically create another draft. No numerical scoring thresholds or model-quality results are invented. Every report has `publication_eligible=false`, including `PASS`. Duplicate detection, deterministic math validation, teacher approval and publication remain separate later work. Numeric/code questions are not offered by the current adapter.

Each prompt uses the pinned local tokenizer and must fit context plus output reservation without silently truncating evidence. The existing generator transport enforces loopback-only Ollama, the supported local tag, maximum 500 MB model file, a conservative free-RAM threshold, CPU-only execution, two threads, context at most 2,048 tokens, output at most 512 tokens, bounded HTTP response, 180-second inference timeout per call and unload requests after each call/error. Both calls use the shared process-local RAG/generation gate. The configured frontend review timeout is 390 seconds. Actual peak RAM, tokenizer parity, model unload behavior, latency and educational quality still require a real hardware trial. The gate is not a distributed queue; use one worker.

Model digest comparison records same/different checkpoint. Even different checkpoints do not establish statistical independence. Prompt delimiting and structured validation do not guarantee prompt-injection resistance or eliminate hallucinations.

## API and storage

All endpoints require an authenticated teacher/student account, enforce ownership, return no-store responses and accept bounded JSON bodies. History is private and only available for the owner's unreleased generated draft.

| Endpoint | Contract |
|---|---|
| `GET /api/v1/verifier/status` | Mode/readiness, candidate model, configured same-model flag, pending hardware status |
| `POST /api/v1/verifier/drafts/{version_id}/reports` | Body: UUID `idempotency_key` only; creates or returns a completed advisory report |
| `GET /api/v1/verifier/drafts/{version_id}/reports?offset=0&limit=3` | Own saved history; maximum page size 10 |

The browser retains a retry key after a failed response and clears it on success. A completed matching retry returns the same report. Reusing the key for another version/configuration is rejected. A successful transaction writes the completed verify job, immutable advisory report and audit event together; a failed write leaves none. The stored evidence includes prompt/policy versions, exact source hash and real-stage metadata only when supplied by actual inference. There is no durable in-progress queue or cross-restart recovery. Navigation may abandon the browser request while backend work finishes; saved history is the recovery surface.

`mcq.verifier_reports` is separate from `mcq.question_verifications` and `mcq.question_releases`. Its constraints reject test-AI claims, publication eligibility, wrong job kind/state, cross-owner links, reports for released drafts and edits/deletes. Neither test reports nor AI advisory reports satisfy existing release gates.

## Validation and technology

See [the completion record](phase-11-completion.md) for actual test counts and evidence. Component/API tests use synthetic model responses; browser tests use test mode. They validate software contracts, not AI answer quality. Embedded PostgreSQL/pgvector checks exercise real SQL and restricted-role behavior; native password authentication and multi-connection contention remain pending.

All reused core technologies are **FREE / OPEN SOURCE**: Python, FastAPI, Pydantic, HTTPX, PostgreSQL, pgvector, React, Vite, Tailwind, local tokenizers and Ollama. No new runtime dependency, paid service, cloud LLM or model weight was introduced. The two requested Gemini API labels are not used as local models.
