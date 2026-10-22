# Phase 11 — verifier workflow

Scope: add private, persisted review reports to Draft studio, with an explicit mock verifier by default and a separated local Ollama adapter. No model downloads or real inference. User-authorized continuation of Phase 10, retaining the lightweight hardware constraint.

The mock path evaluates only deterministic schema/source integrity; semantic quality is NOT_EVALUATED. Test-generated drafts are refused by the real adapter. A real verifier candidate uses two sequential stages: answer the question without its proposed key/explanation, then critique the complete candidate against the same context. Model recommendations remain distinct from approval. Scores/accuracy are not invented. Same-checkpoint generator/verifier calls are disclosed and do not establish independent-model verification.

Add migration 004 for immutable owner/version/job-scoped review reports. Keep reports separate from question_verifications/release gates. Neither mock nor real advisory reports grant publication eligibility. No existing migration edits. Add restricted SELECT/INSERT grants, idempotent report creation and private history/read APIs. One shared compute gate covers indexing, generation and verification. Atomic commits persist a completed job, report and audit event only after checks complete.

Frontend: a review panel beneath a saved draft, mode/status, run/retry controls, categorical results, saved history, explicit pending checks, empty/error/loading states and keyboard/mobile support. Preserve unverified draft labels. No automatic regeneration, verifier approval, math validation, assessment publishing or scoring.

Tests: migration upgrade/replay and report constraints, privacy, idempotency, rollback, source integrity, mock exclusion, strict model output, blind-stage key isolation, sequential calls, changed-model rejection, shared gate, no release writes, UI retries/history and real browser workflow using test fixtures. Real-model quality/hardware trials remain pending. Dependencies are existing FREE / OPEN SOURCE components only.
