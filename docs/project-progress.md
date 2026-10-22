# Project progress — 15 October 2026

**24 of 24 roadmap phases are complete.** Phase 24 delivered the [reviewed 22-slide deck](../../Adaptive_MCQ_Final_Review_Phase24_Final.pptx), [content/speaker notes](../../Presentation_Content_and_Speaker_Notes_Phase24.md), [speaking/viva guide](../../Viva_and_Review_Guide_Phase24.md) and [evidence register](../../Final_Review_Evidence_Register.md). See [Phase 24 completion](phase-24-completion.md). Artifact validation is separate from application testing; no application suite or model inference was rerun. The [Phase 23 handbook](README.md) remains the operating guide.

Phase 22 installed the approved free build tools and pgvector, configured a separate native project database, and passed application startup and recovery acceptance: **58 targeted regression checks, 14 native classroom browser checks and 14 embedded classroom browser checks**. Native backup/restore matched application records and three PDF hashes, revoked restored sessions and allowed fresh sign-in. These remain [Phase 22 evidence](phase-22-completion.md), not new Phase 24 results.

The wider **288 backend tests, 115 frontend tests and 51 foundation browser checks** remain [Phase 21 evidence](phase-21-completion.md); the 119 SQL checks and seven migration-runner checks remain [Phase 20 evidence](phase-20-completion.md). They are not new Phase 24 runs. Phase counts describe roadmap stages, not a measured percentage of effort or production readiness.

## What the website currently contains

**Phase 22 is complete:** supervised local startup, readiness checks, database/PDF backups, non-overwriting restore rehearsal and upload reconciliation are implemented and exercised on native PostgreSQL 18.4 with pgvector 0.8.7. Use the [operator guide](local-deployment.md) to start the project and create your own teacher account.

| Area | Implemented software | Important boundary |
|---|---|---|
| Accounts and roles | Registration, login/logout, password changes, teacher/student access and ownership checks | Native SCRAM, restricted application grants and synthetic classroom accounts tested; no default account in the retained application database |
| Security | API-wide private caching policy, origin/host checks, bounded request handling, upload cleanup, frontend security headers and credential matrix | Native permissions and database restart/restore exercised; whole-machine power-loss recovery and public deployment certification are not established |
| Teacher workspace | Courses/topics, private material library, versioned question review, assessment authoring, publication, participant permissions and reference codes | Mock questions cannot be approved or published |
| Student workspace | Preferences, private materials/test generation, code admission, saved attempts, server grading and released results | Default personal generation is clearly labelled mock/test output |
| Documents and retrieval | PDF extraction/page provenance, chunking, local embedding/indexing and pgvector retrieval | Earlier Phase 9 exercised local embeddings; Phases 20–21 use lightweight tests without fresh model inference |
| Generator and verifier | Separate configurable local roles, structured contracts, source checks, blind-answer/critique stages and guarded sequential execution | Actual LLM quality and hardware suitability remain unvalidated; two roles may use the same checkpoint |
| Quality control | Schema/source checks, duplicate gates, bounded exact arithmetic, immutable edits and teacher approval | Supported arithmetic only; general mathematical proof and broad question-type support are future work |
| Learning and feedback | Topic evidence, provisional difficulty recommendations, next private practice, reports, quarantine and score-review history | Fixed classroom questions remain fixed; learning gains and thresholds are not experimentally validated |
| Analytics | Student/teacher results, topic/difficulty/type breakdowns, feedback counts and optional teacher-only ranking | Operational records are not research accuracy or student-study results |
| Evaluation | Matched condition runner, provenance, human-review packs, missing-data-aware reports and private study export/replay | No real AI experiment, independent human rating study or learner study has been completed |
| Question bank | Persistent questions, versions and teacher review/browsing | Dedicated Question bank navigation screen remains marked Planned |

## What “local and free” currently means

The core design and implementation use local React/Vite, Python/FastAPI, PostgreSQL/pgvector, PyMuPDF, Sentence Transformers and guarded Ollama adapters. No paid API, cloud database, subscription or mandatory hosted deployment is part of the core. Default generator/verifier modes are `mock`; this allows website development and demonstrations without loading an LLM.

The configured tiny model transport is `qwen2.5:0.5b-instruct-q4_K_M`, with separate generator/verifier settings. **Hardware-validated model selection: pending.** Configuration is not a successful hardware benchmark. The 8 GB laptop must not be presented as having demonstrated simultaneous dual-model inference. No Gemini cloud API names are used as local executable models.

The retained local application now uses a dedicated native PostgreSQL/pgvector cluster on 127.0.0.1:55432. Automated classroom acceptance uses separate native or embedded databases and synthetic question evidence. Synthetic eligible questions test the classroom route while normal mock drafts remain blocked. Native startup, database restart and separate database/PDF restore passed; the tests establish engineering behavior, not AI quality or learner outcomes. No LLM was loaded. Browser tests observed no external requests, but the laptop network adapter was not disabled.

## Roadmap closure and open research

There are no remaining numbered phases in the agreed 24-stage roadmap. Completion covers the delivered local engineering demonstrator, documentation and evidence package.

Declared deferrals remain: real local LLM trials, independent-model verification, substantive AI-quality evaluation, broader math/question formats, OCR/languages, learner studies and dedicated Question bank/Recovery tools browser screens. The project must not be described as having validated every original research goal. See [current limitations](limitations.md). Any further work must respect the laptop and the no-heavy-inference constraint.

## Frontend images

The Phase 20 screenshots show the actual running frontend with synthetic accounts and assessment records. They are not AI-generated interface concepts or evidence of experimental performance.

- [Teacher dashboard — desktop](images/phase-20-teacher-dashboard-desktop.png) / [mobile](images/phase-20-teacher-dashboard-mobile.png)
- [Student dashboard — desktop](images/phase-20-student-dashboard-desktop.png) / [mobile](images/phase-20-student-dashboard-mobile.png)
- [Assessment player — desktop](images/phase-20-assessment-player-desktop.png) / [mobile](images/phase-20-assessment-player-mobile.png)
- [Recorded results — desktop](images/phase-20-assessment-results-desktop.png) / [mobile](images/phase-20-assessment-results-mobile.png)
