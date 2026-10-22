# Phase 19 — evaluation harness

**Phase 19 is complete within the local software scope, 14 October 2026.** The harness is implemented; actual AI and learner studies remain to be evaluated.

## Delivered

- Teacher Evaluation lab with isolated synthetic checks, owned immutable saved runs, evidence downloads and operator review bundles.
- Matched A/B/C/D evaluation package: topic-only generation, frozen local RAG, verification of the same candidate, then bounded math validation. Failures and rejected candidates remain in denominators.
- Source/config/prompt/code hashes, seeds, document-separated development/test protocol and a saved development source ledger to prevent exact source leakage.
- Explicitly opt-in local runner with existing tiny-model, token/memory and sequential execution guards. The website cannot request real inference.
- Independent blinded rating templates, two-rater agreement, adjudication, raw/retained metrics, coverage, yield, error counts, stage timings and document-cluster uncertainty.
- Separate consent-confirmed classroom export with fresh pseudonyms and an offline policy replay that never claims counterfactual learning outcomes.
- Migration 012, restricted function grants, API version 0.19.0, [operator guide](evaluation.md) and [review rubric](../evaluation/RUBRIC.md).

## Evidence boundaries

Synthetic tests validate software behavior only. No actual local LLM inference, downloads, real learner experiment, independent human review or AI-quality benchmark was performed. AI correctness, satisfaction and educational gains remain **To be evaluated**. Hardware-validated model selection remains pending.

The current guarded local transport supports only its existing tiny Qwen profile. Separate generator/verifier configuration does not establish independent checkpoints. Frozen-retrieval filtering comparisons do not measure retrieval latency or full regeneration behavior. Source-document bootstrap intervals are exploratory for small samples; they are not paired significance tests. Adaptive replay compares recommendations and cannot estimate answers to unasked questions.

No native database, existing account, secrets or real learner records were changed. Native PostgreSQL/pgvector installation, authentication and multi-connection concurrency remain pending. Apply migration 012 and evaluation runtime grants before using the new page on a native installation. Every core component remains local and free.

## Verification

| Check | Result |
|---|---|
| Full backend regression | 260 passed, one prepared real-embedding test intentionally skipped |
| Final evaluation/replay unit checks | 20 passed, including four additional ordering cases; the three database integrations were covered by the full backend run |
| Frontend regression | 114 passed across 15 files |
| Production build | Passed |
| Database suite | 119 passed: 56 schema/migration, 36 validation/publication, 8 attempt/adaptive, 8 feedback, 6 analytics, 5 evaluation |
| Migration runner | 7 passed |
| Python lint and formatting | Passed; 97 files checked |
| Real browser workflow | 15 checks passed; no page errors or external requests |
| Command-line workflow | Smoke, review pack, blank-rating report and browser-export replay passed; three synthetic replay events and four condition summaries verified |

An ambiguous SQL list query and a syntax error in the new frontend test fixture were corrected before the passing runs. A stalled first frontend run was stopped and replaced by the passing full run. Workspace temporary storage was used after the sandbox rejected a default temporary-directory test. The existing Starlette/httpx deprecation warning remains. No test outcome is an AI-quality or learning-effect result.

## Visual evidence

Screenshots contain **synthetic software fixtures**, not real learner or model results. Desktop 1440 × 1000 and mobile 390 × 844 were inspected; the condition table scrolls horizontally within its mobile panel.

- [Evaluation lab desktop](images/phase-19-evaluation-desktop.png)
- [Evaluation lab mobile](images/phase-19-evaluation-mobile.png)

**19 of 24 phases complete; 5 remain. Next: Phase 20 — integration testing.**
