# Phase 10 — generator LLM and hardware validation

Objective (revised after the user's hardware instruction): complete private draft creation, persistence and navigation using lightweight test generation. Keep a separate CPU/local Ollama adapter for future hardware validation. Do not download model weights or run local LLM inference in this phase. Drafts are not independently verified, approved or published.

Default `GENERATOR_MODE=mock` uses deterministic source excerpts and explicitly labelled placeholder distractors. Test passage selection uses keyword overlap without embedding/model inference; it is not semantic RAG or MCQ quality evidence. Existing semantic RAG remains available independently. `disabled` turns off new drafts; `ollama` is an explicit operator choice and never falls back to mock or a cloud API automatically.

Files: hardware snapshot/local runtime launcher; generator client, prompt/schema/service/routes; source-search generation UI; permission script; backend/frontend/browser tests; measured hardware-trial records and setup/completion guides.

Architecture: current account + owned material → local retrieval → embedding subprocess exits → local Ollama generator → schema and source-reference checks → atomic draft/version/options/provenance storage → private draft preview. Share a compute gate with RAG to avoid overlapping embedding/model work. Four distinct options, answer index, explanation, requested difficulty/cognitive metadata and source quote are required. No numerical/code generation mode in this phase; deterministic numerical validation is Phase 12.

Database: reuse jobs, generation_runs, topics, questions, question_versions, options and question_sources; unverified versions have no release/verification record and cannot be published through existing gates. Store exact retrieved excerpts/hashes, prompt version, model digest and measured inference metadata with the generation run. Create a private topic record when needed, scoped to owner. No schema migration initially expected.

API: generator status, bounded synchronous draft generation with an idempotency key, owned draft read/list. Job rows describe completed persisted generations, not a durable worker queue. No successful generation is acknowledged before draft commit.

Dependencies: Ollama (FREE / OPEN SOURCE), licensed small local model (FREE / OPEN SOURCE), existing HTTPX/Pydantic. No new cloud API or paid service. The runtime and model download are explicit setup; request handlers never install/pull models. Generator/verifier environment variables remain supported. Trial selection depends on reported 8 GB RAM/CPU-only hardware and measured current capacity. Do not claim hardware approval without recorded trials; model quality remains to be evaluated separately.

Tests: local-only URL/model enforcement, bounded output/schema validation, refusal/truncation/unsupported citations, prompt/source separation, ownership and idempotency, no releases, shared compute gate, model failures/no partial draft, persisted provenance, UI status/draft labeling and browser integration with lightweight fixtures. Actual inference trials are deferred per the user's instruction. Preserve native PostgreSQL deployment limitations and all earlier truthfulness requirements.
