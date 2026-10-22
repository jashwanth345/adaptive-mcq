# Current implementation and limitations

**16 October follow-up:** website teacher signup and sequential 10–30-question generation/verification/validation are implemented. See [the current setup and testing guide](question-generation.md). There are still no installed generator/verifier weights or completed real-LLM quality trials. The question-count selector does not turn mock fixtures into educational questions. Batch retry/resume works on the same open page; cross-login batch resumption is not implemented, although saved drafts persist.

Status: **15 October 2026, Phase 24 final review handover**. “Implemented” below means software exists with the linked engineering evidence; it does not mean educational effectiveness is established. Phase counts track delivery stages, not percentage quality or completeness of every original aspiration.

| Area | Implemented / tested | Boundary or future work |
|---|---|---|
| Local website | Authentication, roles, workspaces, navigation, private records and responsive screens | Single-computer demonstrator; not public internet hosting certification |
| PDF processing | Local upload, bounded extraction, page/chunk provenance; the subsequent frontend refresh adds installed Windows offline OCR for up to 10 scanned pages | OCR is platform/language dependent and may misread text; no OCR quality benchmark, pasted-text/topic-only source generation, robust table/equation reconstruction or hard hostile-PDF memory isolation |
| RAG | Local MiniLM embeddings and pgvector retrieval; real offline embedding exercised in Phase 9 | No new Phase 22/23 embedding benchmark; retrieval quality, maximum corpus performance and sustained full-stack RAM remain unmeasured |
| Generator / verifier | Separate configurable adapters, structured contracts, blind solving/critique workflow, mock fixtures and sequential execution guards | No LLM downloaded or run; **Hardware-validated model selection: pending**. Only a narrow tiny-Qwen transport profile is supported; arbitrary tags are not plug-and-play |
| Independence | Distinct generation/review roles and prompts | Same-checkpoint roles are not independent models; correlated failures remain possible. Real independent-checkpoint evidence is absent |
| Validation | Schema, citation integrity, duplicates, bounded exact arithmetic and release blockers | Exact quotes are not factual proof; no general symbolic/formal verification, comprehensive multilingual/semantic duplicate guarantee, or broad numerical/code generation |
| Teacher control | Immutable edits, decisions, approval checks, fixed assessments, permissions and reference codes | Ordinary mock drafts cannot be approved/published. No live classroom bank of real validated AI questions has been established |
| Student attempts | Admission, snapshots, saved answers, deadlines, grading and release policies | No negative marking/partial credit; unsaved answers are not recoverable; expiry is finalized on access, not by a timer daemon |
| Adaptation | Candidate `bounded-performance-v1` policy over eligible evidence; private next-question selection | Thresholds uncalibrated, no causal learning-effect study, no response-time-based ability inference. Fixed classroom tests never adapt. No recommendation without eligible private questions |
| Feedback | Reports/ratings, review triage, confirmed-defect quarantine, score-review tracking | No automatic fine-tuning, prompt self-modification, general regeneration queue, automatic retroactive regrading or notification delivery |
| Analytics | Scoped recorded scores, accuracy breakdowns, feedback counts and optional teacher ranking | These describe operational records, not AI correctness or standardized mastery. Elapsed time includes idle time; per-question response time unavailable |
| Evaluation | Synthetic smoke, matched filtering ablation, human-review packs and private study export/replay | No real AI benchmark, independent completed human ratings, statistical superiority or real learner outcomes |
| Native deployment | PostgreSQL 18.4/pgvector 0.8.7, restricted roles, startup, native transactions, abrupt DB restart, database/PDF restore | Small synthetic acceptance scope; no exhaustive concurrency, whole-machine/power-loss test or automatic live restore cutover |
| User-facing gaps | Questions stored and browsed in Draft studio/Teacher review; recovery CLI works | Dedicated Question bank and Recovery tools browser screens remain Planned; no general course rename/delete screen |
| Account protection | Local passwords, JWT/session revocation, role/ownership checks, throttles and private response policies | No email verification/reset, MFA, HTTPS public deployment or malicious-local-admin protection |

## What the measurements actually support

Phase 22 recorded **58 targeted regression passes**, **14 native classroom browser passes**, and **14 embedded classroom browser passes**. The eight grouped native checks include the browser journey; do not add them as independent samples. Phase 21's wider suites and Phase 20's database suites remain historical evidence and were not rerun in Phase 23.

All classroom fixture users, question approvals, answers and results are synthetic. Test acceptance demonstrates programmed behavior under selected cases. It supplies no factual-accuracy percentage, sample of actual students, model latency benchmark or evidence of improved learning. The retained native application's database was empty of website accounts at the Phase 22 handover; user-created accounts may change that later.

Prepared browser tests rejected external requests and observed none. Model-library offline flags were used and local embedding files checked; the laptop network adapter was not physically disabled. The primary core has no paid API/cloud dependency. Full offline installation still requires previously obtained packages/assets.

## Research and paper claims

The project is inspired by the 2024 MCQGen research and its RAG/refinement/adaptation direction. Existing-paper results belong to that paper, proposed features to the blueprint, and implemented mechanisms to the current source/evidence. No test count in this repository is a reproduction of the paper's experiment. Claims of superiority or novel research require an appropriately controlled comparison and independent evaluation.

The current harness compares topic-only generation, context-grounded generation, verification of the same candidate, and bounded math validation. It does **not** yet test “complete adaptive system versus baseline” as a learner-outcome experiment. A future study must define cohort/task selection, consent/privacy, frozen test materials, independent ratings, denominators, uncertainty and actual hardware measurements before reporting results.

Original diagrams containing Gemini/cloud hosting and illustrative topic percentages are proposals, not current deployment or measured results. The Phase 24 PPT replaces those stack/status claims and labels its synthetic screenshots and illustrative arithmetic. No implementation result should be invented to fill a slide.

## Prioritized future work

1. Maintain the completed Phase 24 presentation, notes and evidence labels whenever verified project behavior changes.
2. Only after a separate hardware decision: validate the smallest feasible local model's memory, tokenizer parity, latency/unload behavior and MCQ quality; keep mocks if unsuitable.
3. Independent human rating and meaningful comparison of grounding, answerability, distractors, diversity and rejection rates; record failures and missing data.
4. Calibrate difficulty/mastery and conduct a properly designed learner study before claiming personalization benefits.
5. Complete deferred question-bank/recovery screens and broader question formats/OCR/languages as explicit additional work.

See [progress](project-progress.md), [Phase 22 evidence](phase-22-completion.md), [security](security.md) and [evaluation protocol](evaluation.md) for details.
