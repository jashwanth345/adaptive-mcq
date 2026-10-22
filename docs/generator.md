# Private draft generation — Phase 10

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

**Phase 11 update:** private advisory review reports are now available in Draft studio; see [verifier.md](verifier.md). They do not approve or publish drafts. The verifier candidate now uses the same small supported Qwen tag below; independent-model and hardware validation remain pending. The phase-specific discussion below records the generator boundary.

## Available now

Both teachers and students can open **Draft studio** from the sidebar, or select a PDF in **Study materials → Open Draft studio**. Choose a topic occurring in that PDF, select target difficulty/cognitive level, and create a private test draft. The saved preview includes four options, proposed answer, explanation and an exact page-cited source quotation. Navigate away and reopen it from Saved drafts. All content remains account-scoped.

Default **Test mode — no AI inference** is a deterministic fixture. It copies the first part of a keyword-matched passage and supplies three explicitly labelled placeholder distractors. It does not assess learning, produce educational-quality questions, adapt difficulty or measure mastery. The separate semantic search interface from Phase 9 remains available; test draft selection does not call that embedding worker. This keeps website development independent of available LLM memory.

No approval, publishing, scoring, verification or mathematical-validation action exists in this phase. No question release or verification record is inserted. Test records carry `mode=mock`, `model=deterministic-test-fixture`, `digest=not-an-llm` and `retrieval=keyword_test`; these must remain excluded from future quality evaluations and publication workflows.

## Local setup

Use the existing backend, authentication, material and RAG setup guides and local PostgreSQL/pgvector database. As the trusted database owner, apply the additive permission script after the Phase 4–9 scripts:

```powershell
psql -h 127.0.0.1 -U <database-owner> -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f database/generator_runtime_grants.sql
```

The restricted backend role receives draft inserts/reads, not publication or verification writes. Source locking needs column-level UPDATE permission on question version `id`; the immutable-version trigger still rejects updates. This is an application-enforced ownership design: the shared backend database role can read records, while every private API scopes access to the authenticated owner. Database credentials must never be given to browser clients.

In the project `.env`, retain private database/JWT settings and use:

```dotenv
GENERATOR_MODE=mock
MODEL_SELECTION_STATUS=pending_hardware_validation
GENERATOR_MODEL=qwen2.5:0.5b-instruct-q4_K_M
VERIFIER_MODE=mock
VERIFIER_MODEL=qwen2.5:0.5b-instruct-q4_K_M
LLM_CONTEXT_TOKENS=2048
LLM_OUTPUT_TOKENS=512
```

The configured names are candidates only, not installed models or validated choices. The verifier is not called. **Hardware-validated model selection: pending.** Mock mode ignores model weights and needs no Ollama process. Start the local database, existing backend launcher and frontend as documented in `backend.md` and `frontend.md`. No production database, account, secret or `.env` was created by this phase.

Native PostgreSQL/pgvector setup remains an existing deployment prerequisite. Disposable database tests do not install or validate a native Windows database service.

## Explicit modes

| Mode | Behavior | Model requirements |
|---|---|---|
| `mock` (default) | Keyword-selected excerpt and placeholder options; always labelled test data | None; no embedding/LLM calls |
| `disabled` | Existing drafts can be read; new generation rejected | None |
| `ollama` | Owned semantic retrieval, prompt preparation, structured local inference and private unverified draft | Explicit future setup and hardware trial |

The mode is a backend setting, not a client-controlled request field. No automatic fallback, model pull, cloud request or installation occurs during an API request.

## Local LLM adapter — implemented, inference unvalidated

The current adapter supports only `qwen2.5:0.5b-instruct-q4_K_M`, paired with a pinned local Qwen2.5 tokenizer. It rejects other model tags until their tokenizer/context handling is explicitly supported and tested. This is a conservative initial adapter, not a claim that this checkpoint meets academic MCQ quality requirements. Models can be configured through environment variables without modifying call sites; unsupported configurations fail clearly.

The pipeline is owned PDF → existing semantic retrieval → embedding subprocess exits → token-budgeted ChatML prompt → loopback Ollama → strict structured-output parsing → exact citation/quotation check → atomic private draft storage. It does not prove factual correctness. Numerical and code question modes are not offered.

Before inference, the adapter checks the exact local tag/digest, size at most 500 MB, absence of cloud-model metadata, and at least `max(1.5 GiB, model bytes + 1 GiB)` free physical RAM. This is a conservative gate, not a measured peak-memory guarantee. It uses CPU only, two inference threads, at most 2,048 context tokens and 512 output tokens, one shared process-local compute gate, no retries, 180-second inference timeout, a 1 MiB HTTP response cap and model unload requests after completion/error. Only one backend worker should run. Future verifier execution must use the same gate and unload the generator before loading another model.

Raw ChatML and a hash-checked pinned tokenizer bound input tokens plus reserved output space. Source/topic text is JSON-encoded; ChatML delimiter strings inside untrusted content are escaped. The reported prompt-token count must match the locally measured count within two tokens. This contract has fixture tests, but actual Ollama tokenizer parity, inference latency, cancellation/unload behavior and MCQ quality remain unvalidated. Prompt framing reduces accidental instruction mixing; it does not guarantee prompt-injection resistance.

The explicit optional setup utility `python -m backend.prepare_generator` downloads tokenizer files only. `python -m backend.run_ollama` starts an already prepared portable runtime with loopback binding, cloud disabled, one model and workspace-local model storage. Neither is needed in mock mode. The runtime has not been launched in this phase; actual service startup may require normal Ollama user-profile files. Do not activate inference automatically on this laptop.

## API and persistence

All routes require authentication and return `Cache-Control: no-store`. JSON bodies are bounded to 16 KiB.

| Endpoint | Contract |
|---|---|
| `GET /api/v1/generator/status` | Effective mode, readiness, measured RAM and pending model-selection status |
| `POST /api/v1/generator/drafts` | One draft from 1–3 owned materials; topic 2–100 characters; easy/medium/hard; remember/understand; UUID idempotency key |
| `GET /api/v1/generator/drafts?offset=0&limit=6` | Own private unreleased drafts; limit at most 20 |
| `GET /api/v1/generator/drafts/{version_id}` | Own private unreleased draft with proposed key and source evidence |

The browser retains the same idempotency key when retrying the same form after a network failure. A completed retry returns the original saved draft. Reusing a key with changed parameters is rejected. A new successful creation clears the key. Navigation can abandon the browser request while the synchronous backend completes; reopening saved history reveals committed work. There is no durable background queue or cross-restart in-progress job recovery yet.

One database transaction writes a private topic if needed, completed generation job, immutable generation run, question/version, four options, exact source evidence and audit event. Failed generation/citation checks create no success record. Generation metadata records the mode, prompt version, local model identity, settings, retrieved excerpts/hashes, requested targets and available inference measurements. Mock records never contain invented AI latency or accuracy.

## Technology classification

All core dependencies used here are **FREE / OPEN SOURCE**: Python, FastAPI, PostgreSQL, pgvector, HTTPX, Pydantic, React, Vite, Tailwind, tokenizers and Ollama. The candidate Qwen2.5 0.5B model is Apache-2.0 according to its published model listing. Existing PDF processing uses PyMuPDF's open-source edition. No additional paid dependency or account was introduced.

References: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [Ollama Windows distribution](https://docs.ollama.com/windows), [Qwen2.5 0.5B Q4_K_M listing](https://ollama.com/library/qwen2.5:0.5b-instruct-q4_K_M).
