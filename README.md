# Adaptive MCQ Generation Using Dual LLMs with Student Feedback

## Current project status — 22 October 2026

A local B.Tech assessment platform with teacher/student accounts, PDF processing, RAG, sequential local generator/verifier adapters, teacher review, classroom assessments, reference codes, feedback and analytics. Core execution requires no paid API or cloud service.

**Real MCQ generation is not yet verified on the development laptop.** Its 8 GB RAM is heavily occupied; the latest check found 0.44 GiB available, below the 1.5 GiB inference guard. The 398 MB Qwen candidate is installed on that laptop but is not included in this repository. Mock questions are labelled and cannot be published. Passing application tests is not proof of LLM accuracy.

- **New installation:** [GitHub clone and local setup](docs/github-setup.md).
- **Already configured laptop:** run `Start-Project.cmd`, then open `http://localhost:5173`.
- **Latest verified fixes and limits:** [local AI, course selection and assessment saving](docs/local-ai-fix-verification.md).
- **Review package:** [final presentation](docs/review/Adaptive_MCQ_Final_Review_Phase24_Final.pptx), [speaker notes](docs/review/Presentation_Content_and_Speaker_Notes_Phase24.md), [viva guide](docs/review/Viva_and_Review_Guide_Phase24.md), [master blueprint](docs/review/Project_Master_Blueprint.md).

Source code, migration scripts, tests and review documents are included. Private configuration, accounts/database contents, uploaded PDFs, logs, model weights and installed dependencies are excluded. GitHub stores this source; GitHub Pages cannot run the Python/PostgreSQL/Ollama application.

## Historical implementation records

The phase notes below describe their dates, not current runtime readiness. Current instructions and limitations above take precedence.

**16 October update:** [Teacher signup, 10–30-question batches and local AI setup](docs/question-generation.md).

**Interface refresh:** the current website adds a public landing page, clearer teacher/student dashboards, blue/violet styling, PDF drag-and-drop and installed Windows offline OCR for scanned PDFs. See the [refresh and verification record](docs/frontend-refresh.md). Earlier phase sections and the Phase 24 deck below remain dated historical evidence.

**Phase 24 complete, 15 October 2026: final evidence, 22-slide presentation, speaker notes and viva package delivered. All 24 roadmap phases are complete with the stated feature/research deferrals. Default AI remains mock; real model quality and learning benefits remain To be evaluated.**

Current instructions: [documentation index](docs/README.md), [setup](docs/setup-guide.md), [user guide](docs/user-guide.md), [demonstration script](docs/demo-script.md), [limitations](docs/limitations.md).

Start the configured local website with [Start-Project.cmd](Start-Project.cmd). Create your first teacher account with [Create-Teacher.cmd](Create-Teacher.cmd), supplying your own identity and password. See the [local operating guide](docs/local-deployment.md). Earlier phase sections below record their historical status; Phase 22 resolves their native-setup blockers and Phase 23 supplies the current user documentation.

This folder contains the specifications, database migrations, local authentication backend, teacher course/topic dashboard, student activity/preferences dashboard, private PDF library, local semantic source retrieval and private Draft studio. Teachers and students can save/reopen clearly labelled test drafts and private advisory review reports without loading an LLM. Teachers can inspect, edit new versions and reject questions in Teacher review. Approval requires fresh passing real evidence; mock content stays blocked after editing. Teachers can now author and publish eligible classroom assessments and manage expiring reference codes. Students can join permitted assessments, save/resume attempts and view released server-graded results. My learning derives provisional topic profiles and recommends eligible private practice. Students can report/rate completed questions; owners can review and quarantine confirmed defects without rewriting historical scores. My analytics and Classroom analytics now show source-derived results, breakdowns, feedback counts and an optional teacher-only assessment ranking. Evaluation lab now provides isolated synthetic comparisons, evidence/review downloads and a separate private study export. Real AI quality, independent-model verification and learning benefits remain unvalidated.

The architecture specifies a free local core: React, Vite, Tailwind, Python/FastAPI, PostgreSQL/pgvector, PyMuPDF, Sentence Transformers, Ollama and bounded Python exact-arithmetic validation. Broader symbolic math remains future work. Source retrieval is implemented. The generator/verifier adapters have fixture tests but no actual inference validation. Per the user's revised instruction, default test generation and validation avoid LLM inference; existing semantic RAG remains separately available. Future LLMs must load sequentially after hardware validation. No paid API or mandatory cloud service is part of the baseline.

## Phase 1 documents

- [Requirements and acceptance checklist](docs/requirements.md): scope, roles and traceable acceptance scenarios.
- [Architecture and decisions](docs/architecture.md): boundaries, state transitions, data relationships and reasons.
- [Hardware and dependency readiness](docs/readiness.md): observed local checks, limitations and pending model benchmark.
- [Development and validation plan](docs/development.md): exact phase boundary, dependencies, future checks and handoff.
- [Phase 1 completion record](docs/phase-1-completion.md): delivered files, checks performed and remaining setup work.
- [.env.example](.env.example): backend configuration template; no credentials are supplied.

The research and project context remain in the [40-section master blueprint](docs/review/Project_Master_Blueprint.md). The [final presentation](docs/review/Adaptive_MCQ_Final_Review_Phase24_Final.pptx), [speaker notes](docs/review/Presentation_Content_and_Speaker_Notes_Phase24.md) and [viva guide](docs/review/Viva_and_Review_Guide_Phase24.md) remain the review artifacts. Phase completion records supersede the original roadmap's waiting statuses. The Phase 24 package reflects dated implementation evidence and explicit research limits; it does not supersede the latest AI validation status above.

## Phase 2 database

- [Database design and setup](docs/database.md): tables, relationships, transaction contracts, migration commands and reproducible tests.
- [Phase 2 scope](docs/phase-2-plan.md): objective, files, dependencies and test plan.
- [Phase 2 completion](docs/phase-2-completion.md): actual results and remaining deployment checks.
- [Migration runner](database/migrate.py) and [SQL migrations](database/migrations/001_core.sql).

**Phase 2 validation: 40 database checks + 7 migration-runner tests passed.** SQL execution used embedded PostgreSQL with pgvector. Native Windows PostgreSQL startup was blocked by sandbox restrictions, and native pgvector installation is still required. No existing PostgreSQL data was migrated.

## Phase 3 backend

- [Backend setup and API contracts](docs/backend.md): startup, secrets, permissions, diagnostics and reproducible checks.
- [Phase 3 scope](docs/phase-3-plan.md) and [completion report](docs/phase-3-completion.md).
- [Application factory](backend/app/main.py) and [dependency lockfile](backend/requirements.txt).

**Phase 3 validation: 55 backend tests passed** at its completion. The expanded Phase 4 results are below. Native PostgreSQL authentication/deployment remains pending.

## Phase 4 authentication

- [Authentication setup and API guide](docs/authentication.md): student registration, login/logout, password changes, teacher enrollment, permissions and tests.
- [Phase 4 completion and validation](docs/phase-4-completion.md).
- [Authentication migration](database/migrations/003_auth.sql), [runtime grants](database/auth_runtime_grants.sql) and [local operator command](backend/manage.py).

**82 backend tests, 41 SQL/schema checks and 7 migration-runner tests passed.** Passwords use Argon2id; short-lived JWTs are checked against active database sessions and current roles. Teacher enrollment is an operator-only action. No real account, password or active `.env` is supplied. Apply migration 003 and the restricted grants before using authentication on the native database.

From this project root, after supplying the required local configuration and secrets:

```powershell
.\.venv\Scripts\python.exe -m backend.app
```

The [run guide](docs/backend.md) explains first-time environment setup. While running, open `http://127.0.0.1:8000/docs` for offline API documentation. Liveness can succeed while database readiness returns 503; this intentionally makes missing setup visible. No server is left running by the tests, and no active `.env` has been saved.

Readiness checks found Python 3.13.1, Node.js 22.19.0, npm 10.9.3, Git 2.54.0 and PostgreSQL client 18.4. PostgreSQL did not respond on 127.0.0.1:5432 during the check. pgvector was not found in that PostgreSQL installation, and Ollama was not found on PATH or at its default executable path. About 60.5 GiB was free on the workspace C: drive. This is a point-in-time observation, not a sustained hardware benchmark.

**Hardware-validated model selection: pending.** The 398 MB `qwen2.5:0.5b-instruct-q4_K_M` candidate is now installed for both roles. Same-checkpoint sequential calls are not independent-model verification. The local trial remains blocked by insufficient free RAM; no real MCQ-quality or learning-outcome results are available. `Start-Project.cmd` now uses local AI when this model is installed. See [current verification and remaining limitations](docs/local-ai-fix-verification.md).

## Phase 5 frontend

- [Frontend startup and behavior](docs/frontend.md): local launch, screens, session handling and tests.
- [Phase 5 completion](docs/phase-5-completion.md): delivered scope and validation limitations.
- [Frontend source](frontend/src/App.tsx) and [pinned dependencies](frontend/package.json).

**29 frontend tests and 12 real-browser checks passed; strict TypeScript checks and the production build passed.** The interface supports registration, login, role-based workspace navigation, account identity, password changes and sign-out. Assessment/AI capabilities remain Planned. Tokens stay in memory and are lost on refresh. Browser testing used disposable PostgreSQL and synthetic accounts; native database setup remains required for everyday use.

From this project root, with the backend running in another terminal:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run dev
```

Open `http://localhost:5173`. Packages download once; normal frontend use needs no cloud service. See the [run guide](docs/frontend.md) for prerequisites.

## Phase 6 teacher dashboard

- [Teacher dashboard setup and API guide](docs/teacher-dashboard.md).
- [Completion and validation report](docs/phase-6-completion.md).
- [Required runtime grants](database/teacher_runtime_grants.sql).

Teachers can now create courses, add topics and read their own stored counts and recent classroom assessment records. The dashboard includes loading, empty, error and retry states. Students and other teachers cannot access an owner's courses through these routes. No new migration is required; apply the permission script with the trusted database-owner login before normal use.

**36 frontend tests and 17 real-browser checks passed; build and Ruff passed.** The backend run verified 91 distinct checks across the initial suite and two corrected-expectation rechecks. Test accounts and course records were disposable fixtures. Native PostgreSQL/pgvector setup remains pending, and no AI-quality experiment was performed.

## Phase 7 student dashboard

- [Student setup and API guide](docs/student-dashboard.md).
- [Completion and validation report](docs/phase-7-completion.md).
- [Required student permissions](database/student_runtime_grants.sql).

Students can now see their own stored activity counts, recent active enrollments and paginated attempt metadata, and save a starting-difficulty preference for future practice. No answer keys, scores or simulated mastery are shown. No migration is required; the trusted database operator must apply the new permission script for normal local use.

**99 distinct backend checks, 42 frontend tests and 20 browser checks passed; the build and Ruff passed.** Backend checks comprise a 98-test suite plus a separately added positive-record privacy test. Test data was disposable. Native PostgreSQL/pgvector setup remains pending.

## Phase 8 PDF materials

- [PDF setup, API and recovery guide](docs/materials.md).
- [Phase 8 scope](docs/phase-8-plan.md) and [completion record](docs/phase-8-completion.md).
- [Material runtime grants](database/material_runtime_grants.sql): apply as the trusted database operator; existing migrations are unchanged.

Teachers and students can upload private text PDFs, inspect page-linked passages, and reopen stored materials. Processing is local with PyMuPDF; no embedding or LLM runs. Limits are 5 MiB / 100 pages per document and one ingestion at a time. Duplicate bytes reuse the owner's existing document. The UI explicitly reports unsupported image-only/encrypted PDFs.

Native PostgreSQL/pgvector setup remains pending. Tests use disposable database fixtures and temporary uploads; no real application account or `.env` was created. See the completion record for actual verification and remaining boundaries.

## Phase 9 local RAG retrieval

- [Local RAG setup and behaviour](docs/rag.md), including the one-time free embedding model preparation.
- [Phase 9 scope](docs/phase-9-plan.md) and [completion record](docs/phase-9-completion.md).
- [RAG runtime grants](database/rag_runtime_grants.sql): apply as the trusted operator; existing migrations remain unchanged.

Select a PDF in **Study materials**, prepare it for search, and find page-cited source passages. CPU-only Sentence Transformers runs the pinned local MiniLM snapshot. PostgreSQL/pgvector searches only the authenticated owner's selected documents and current model revision. Results have citations and explicit insufficient-evidence handling; no MCQ or answer is generated. The local embedding model is prepared in this workspace, while native PostgreSQL/pgvector setup remains pending.

The Phase 9 retrieval boundary is extended by the Phase 10 private-draft workflow below. Hardware-validated generator/verifier model selection remains pending.

**Phase 9 verification: 123 distinct backend checks, 51 frontend tests and 26 browser checks passed**, including real offline CPU embedding and browser-to-pgvector retrieval. The backend total combines the 122-test regression suite and one added recovery test. Build, Ruff and dependency consistency passed. See the completion record for evidence and deployment limits.

## Phase 10 generator foundation and lightweight draft workflow

- [Draft studio setup and API guide](docs/generator.md).
- [Hardware evidence and deferred inference](docs/phase-10-hardware.md).
- [Revised phase scope](docs/phase-10-plan.md) and [completion record](docs/phase-10-completion.md).
- [Generator runtime grants](database/generator_runtime_grants.sql): apply after Phase 4–9 grants as the trusted database operator. No migration change.

Open **Study materials → select a PDF → Open Draft studio**, or use the sidebar. With `GENERATOR_MODE=mock`, draft creation uses keyword-matched excerpts and placeholder distractors, visibly marked **Test draft — not AI-generated**. Saved drafts are private and cannot be published/scored. `disabled` and explicit `ollama` modes are available; there is no automatic fallback or model download.

**143 distinct backend checks, 56 frontend tests and 29 lightweight browser checks passed.** The actual embedding-model regression was intentionally skipped in this phase; Phase 9's real embedding evidence remains separately recorded. Local LLM weights were not downloaded and no LLM inference ran. Native PostgreSQL/pgvector deployment remains pending. See the completion record for test composition and limitations.

## Phase 11 verifier workflow

- [Verifier setup, modes and API guide](docs/verifier.md).
- [Phase scope](docs/phase-11-plan.md) and [completion evidence](docs/phase-11-completion.md).
- [Advisory-report migration](database/migrations/004_verifier_reports.sql) and [restricted runtime grants](database/verifier_runtime_grants.sql).

Open a saved draft's **Verification workspace**, run a test review and reopen its private report history. Default reports check question format and source integrity, explicitly mark AI quality as not evaluated, and cannot approve or publish a question. The separate local adapter answers without the proposed key before a second critique call; actual inference is still unvalidated. No model weights, cloud service or new paid dependency are required.

Apply migration 004 and its runtime grants as the trusted local database operator before normal use. Native PostgreSQL/pgvector deployment remains pending. The next roadmap phase is **Phase 12: mathematical/duplicate validation and release gates**.

**Phase 11 validation: 159 backend checks, 49 database checks, 7 migration-runner checks, 62 frontend checks and 32 lightweight browser checks passed.** The production build and Ruff passed. One real embedding-model regression was intentionally skipped; no LLM inference or research-quality evaluation ran. See the completion record for reproducible evidence and remaining deployment limitations.

## Phase 12 validation and release gates

- [Validation setup, supported math and API guide](docs/validation.md).
- [Phase scope](docs/phase-12-plan.md) and [completion evidence](docs/phase-12-completion.md).
- [Migration 005](database/migrations/005_validation.sql) and [restricted grants](database/validation_runtime_grants.sql).

Open an owned draft's **Validation workspace** to save schema/source checks, duplicate candidates, math results and explicit release blockers. Test content remains blocked. **Try the arithmetic checker** provides an unsaved exact-calculation preview; equivalent numeric options, missing/wrong keys and undefined operations fail. General word problems, units, rounding and symbolic algebra are unsupported.

The database requires current passing evidence, an unchanged comparison corpus and an eligible owner/reviewer before release and new publication. Classroom assessments require teacher approval; the future private-practice path may use eligible automatic student release. Phase 12 exposed neither release nor publication actions; Phase 13 adds teacher approval below. Apply migration 005 and its additive grants before normal native use; no production database was changed here.

The subsequent phase is **Phase 13 — teacher review, versioned editing and approval**, described below. Hardware-validated model selection and native PostgreSQL/pgvector deployment remain pending.

**Phase 12 validation: 191 backend checks, 70 database checks, 7 migration-runner checks, 68 frontend checks and 35 lightweight browser checks passed.** Final build and Ruff passed. One real embedding-model test was intentionally skipped. Duplicate policy and arithmetic support have the explicit limits documented above; no AI-quality measurements were invented.

## Phase 13 teacher review and versioned approval

- [Teacher workflow, evidence model and API guide](docs/teacher-review.md).
- [Phase scope](docs/phase-13-plan.md) and [completion evidence](docs/phase-13-completion.md).
- [Migration 006](database/migrations/006_teacher_review.sql) and [restricted runtime grants](database/review_runtime_grants.sql).

Open **Teacher review** from the sidebar or an owned draft. Inspect the source, save edits as new immutable versions, record rejection reasons or explicitly approve a version with current passing evidence. Editing quarantines the previous release and requires fresh AI review/validation. Test questions cannot be approved, even after editing. An approval references categorical reports without inventing legacy numerical quality scores.

Approval does not publish an assessment. The app receives narrow review-function permissions, not direct release or assessment writes. Apply migration 006 and its grants through the trusted local operator process before normal native use. All development evidence uses disposable fixtures; no retained database or production account was changed.

The subsequent phase is **Phase 14 — assessment publication and reference codes**. The core remains free and local; hardware-validated model selection is pending.

**Phase 13 validation: 202 backend tests, 79 database checks, 7 migration-runner tests, 75 frontend tests and 42 lightweight browser checks passed.** Final build and lint passed. The seven teacher UI tests also passed after the final editor-label/style corrections. One real embedding-model test was intentionally skipped. See the completion record for test boundaries, screenshots and native-deployment limitations.

## Phase 14 classroom publication and reference codes

- [Workflow, API and local setup](docs/assessments.md).
- [Phase scope](docs/phase-14-plan.md).
- [Completion and verification report](docs/phase-14-completion.md).
- [Migration 007](database/migrations/007_assessments.sql) and [restricted runtime grants](database/assessment_runtime_grants.sql).

Teachers can save fixed classroom drafts, permit registered students, publish approved question versions and issue, replace or revoke expiring reference codes. Publication and initial code creation are atomic. Published questions/settings are immutable; mock-generated content stays blocked. Students can join authorized assessments and see metadata without answer keys or private material. Joining does not start an attempt.

The subsequent phase is **Phase 15 — assessment attempts and scoring**. Native PostgreSQL/pgvector setup and Hardware-validated model selection remain pending.

**Phase 14 verification: 215 backend tests, 88 database checks, 7 migration-runner checks, 84 frontend tests and 48 lightweight browser checks passed.** Build and lint passed. One real embedding test was intentionally skipped. Final database/browser verification includes the attempt-trigger lock-order correction. Positive publication tests use synthetic evidence; no model inference or research-quality measurements were performed.


## Phases 15 and 16 — attempts and adaptive practice

- [Workflow, API, setup and policy](docs/attempts-and-adaptive.md).
- [Combined phase scope](docs/phase-15-16-plan.md) and [completion evidence](docs/phase-15-16-completion.md).
- [Attempt migration 008](database/migrations/008_attempts.sql), [adaptive migration 009](database/migrations/009_adaptive.sql), [attempt grants](database/attempt_runtime_grants.sql) and [adaptive grants](database/adaptive_runtime_grants.sql).

Students can start/resume admitted classroom assessments, navigate pinned shuffled items, save choices and review flags, and submit for idempotent server grading. Time/attempt limits and result-release policies are enforced. Released results show stored solutions and supporting excerpts; withheld results do not leak keys or learning signals.

My learning derives topic profiles from eligible first responses, shows evidence coverage and recommends eligible unseen private practice. Difficulty changes are bounded; the index and thresholds are provisional and **to be evaluated**. An empty or test-only question bank does not become scored practice. Fixed classroom assessments remain fixed.

**Verified: 226 backend tests, 97 database checks, 7 migration-runner tests, 92 frontend tests and 57 browser checks passed.** Build and lint passed. One real embedding-model check was intentionally skipped. Positive tests use synthetic evidence; they are not model-quality experiments. See the completion report for screenshots and boundaries.

**16 of 24 implementation phases are complete. Next: Phase 17 — student feedback, version reports, quarantine and review.** Native PostgreSQL/pgvector deployment, real concurrency and Hardware-validated model selection remain pending. No paid dependency or model download was introduced.


## Phase 17 — student feedback, quarantine and review

- [Student/owner workflow, API and policy](docs/feedback.md).
- [Phase scope](docs/phase-17-plan.md) and [completion report with screenshots](docs/phase-17-completion.md).
- [Migration 010](database/migrations/010_feedback.sql) and [restricted feedback grants](database/feedback_runtime_grants.sql).

Completed attempts accept version-linked issue reports and helpful/poor ratings. My feedback preserves each student's reports. Owners review distinct-reporter/exposure counts, notes and history, then mark reviewing, dismiss or explicitly confirm a defect. Counts prioritize review; they do not prove an error or automatically quarantine content.

Confirmed versions cannot be reused or reapproved. Past scores remain unchanged and under review, defective solutions are withheld, and adaptive evidence is excluded. Score-review acknowledgement records follow-up without regrading; late completions reopen review. Teachers create corrected immutable versions through the existing editor and fresh approval gates. Private students can review only their own practice content.

**Verification: 236 backend tests, 106 database checks, 7 migration-runner tests, 100 frontend tests and 14 feedback browser checks passed.** The final feedback/teacher API recheck passed 21 tests within the backend scope. Build and lint passed. One real embedding test was intentionally skipped. Positive fixtures are synthetic workflow evidence, not AI-quality results.

**17 of 24 phases complete; 7 remain. Next: Phase 18 — analytics.** Native PostgreSQL/pgvector deployment, real concurrency and Hardware-validated model selection remain pending. No paid dependency, model download or AI inference was added.


## Phase 18 — analytics

- [Completion and verification](docs/phase-18-completion.md), [metric definitions and API](docs/analytics.md), [phase scope](docs/phase-18-plan.md).
- Student **My analytics** and teacher **Classroom analytics**: counts, recorded average score, answered-item accuracy, elapsed time, topic/difficulty/type breakdowns and history.
- Teacher assessment-specific analysis, most-missed questions, feedback signals and optional teacher-only best-attempt ranking. Student-withheld results stay out of student aggregates.
- Quarantined items leave original scores intact but are excluded from accuracy/breakdowns/ranking. Zero denominators show No data; per-question timing is not invented.
- [Migration 011](database/migrations/011_analytics.sql) and [restricted analytics grants](database/analytics_runtime_grants.sql) are required for native setup.
- Verification: **241 backend tests passed**, one prepared-embedding test skipped; **108 frontend tests**, **113 database checks**, **7 migration-runner tests**, **12 browser checks** passed. Production build and Python lint passed. All workflow data were synthetic; no model inference ran.

**18 of 24 phases complete; 6 remain. Next: Phase 19 — evaluation harness.** Native PostgreSQL/pgvector setup and Hardware-validated model selection remain pending. No paid services or model downloads were added.


## Phase 19 — evaluation harness

- [Completion and verified checks](docs/phase-19-completion.md), [operator guide and endpoints](docs/evaluation.md), [human review rubric](evaluation/RUBRIC.md).
- Teacher **Evaluation lab** runs isolated synthetic checks, saves owned evidence and downloads blinded review bundles. These candidates cannot become classroom questions.
- Matched topic-only / frozen RAG / verifier / math comparisons retain failures, provenance, denominators and raw/retained quality. Missing independent ratings remain **To be evaluated**.
- A separate consent-confirmed private export supports offline adaptive-policy replay without claiming learning gains.
- [Migration 012](database/migrations/012_evaluation.sql) and [restricted evaluation grants](database/evaluation_runtime_grants.sql) are required for native setup.
- Verification: **260 backend regression tests**, **20 final evaluation/replay unit checks**, **114 frontend tests**, **119 database checks**, **7 migration-runner tests** and **15 browser checks** passed. One real-embedding check was intentionally skipped. Build, lint, visual review and CLI export/report/replay checks passed. Unit and full-regression counts overlap; they are not additive.

**19 of 24 phases complete; 5 remain. Next: Phase 20 — integration testing.** No real model inference or learner experiment was run. Hardware-validated model selection and native PostgreSQL deployment/concurrency remain pending. The core remains free and local.

## Phase 20 — integration testing

- [Completion evidence and actual screenshots](docs/phase-20-completion.md), [current project progress](docs/project-progress.md), [integration test guide](docs/integration-testing.md).
- Connected teacher publication, code replacement, student admission, saved attempts, clean API restart, safe retry after lost responses, submission, analytics, feedback, quarantine, mastery and evaluation export.
- Fixed an outdated success notice remaining visible after a failed attempt reload. Added a component regression and browser failure/recovery checks.
- Verification: **264 backend tests**, **119 database checks**, **7 migration-runner tests**, **48 foundation browser checks** and **14 classroom browser checks** passed. Frontend regression passed **114 tests**, followed by **9 final attempt checks** after the fix (eight overlap). Build, lint and desktop/mobile visual inspection passed. One real-embedding test was intentionally skipped.
- Screenshots and positive classroom approvals use explicitly synthetic fixtures. Mock-generated drafts remain blocked from publication. No real inference, model download, paid service or learner experiment was introduced.

**20 of 24 phases complete; four remain. Next: Phase 21 — security hardening.** Phases 22–24 cover local deployment/recovery, final documentation and final evidence/presentation updates. Native PostgreSQL authentication/concurrency, forced-kill recovery, Hardware-validated model selection and real AI-quality evaluation remain pending. The separate Question bank screen remains marked Planned.

## Phase 21 — security hardening

- [Completion evidence](docs/phase-21-completion.md), [security guide](docs/security.md), [current project progress](docs/project-progress.md).
- API-wide private-response caching protection, strict browser origin checks, bounded request sizes/read time, malformed length/encoding rejection and early oversized-PDF rejection with cleanup checks.
- Frontend preview security policies restrict scripts and connections to the local origin, prevent framing and disable unused browser permissions. Development refresh has a documented exception.
- Updated `setuptools` to 83.0.0 after advisory review. Saved audits report zero remaining matches within their documented package coverage; this is not a security certification.
- Verification: **288 backend tests, 115 frontend tests, 51 foundation browser checks and 14 classroom browser checks passed**. The final **7 upload checks** passed after the last assertion was added and overlap the backend suite. One real-embedding test was intentionally skipped. Build, lint and dependency compatibility passed.

**21 of 24 phases complete; three remain. Next: Phase 22 — local deployment and recovery.** Native PostgreSQL authentication/concurrency, durable recovery and prepared offline startup remain pending. No real model inference or learner experiment ran; mock generation stays the default and mock drafts remain blocked from publication. The core remains free and local.

## Phase 22 — local deployment and recovery

- [Startup and recovery guide](docs/local-deployment.md), [completion evidence](docs/phase-22-completion.md), [phase scope](docs/phase-22-plan.md).
- New local operator commands: `configure`, `doctor`, `start`, `reconcile`, `backup`, `verify-backup`, `restore`. Run with `.venv/Scripts/python.exe -m deployment.local` from this directory.
- Supervised prepared frontend/backend startup uses mock AI and refuses missing database prerequisites. No package/model download or cloud fallback occurs at startup.
- Backups include a database snapshot and verified referenced PDFs; restore uses a separate empty database and staging folder, preserving the live configuration/uploads. Orphan reconciliation never deletes files.
- Installed the approved free Microsoft C++ build tools and built pgvector 0.8.7 from official source for PostgreSQL 18.4. A separate project cluster on 127.0.0.1:55432 now has all 12 migrations and 15 runtime grant files, private configuration and restricted application credentials.
- Native application checks passed for authentication, vector operations, independent transaction contention, abrupt database restart and complete database/PDF backup and separate restore. Restored records and PDF hashes matched; old sessions were revoked and fresh sign-in worked. Prepared local website startup and clean shutdown passed.
- Verification: **58 targeted regression checks, 14 native classroom browser checks and 14 embedded classroom browser checks passed**. All classroom fixtures are synthetic; no model was downloaded or run.

**22 of 24 phases complete; two remain.** Private database/JWT secrets were generated; no default website account was created. Next: Phase 23 — final documentation, then Phase 24 — final evidence and presentation update. These phases have not started. Whole-machine power-loss recovery and real AI-quality evaluation remain unvalidated.

## Phase 23 — final documentation

- [Current documentation index](docs/README.md), [completion report](docs/phase-23-completion.md) and [scope](docs/phase-23-plan.md).
- Setup, teacher/student user guide, troubleshooting, review demonstration script, current limitations and maintainer handover are consolidated against implemented behavior. Older module references are explicitly marked as historical.
- Documentation links, routes and launcher references were checked; no application suite, LLM inference or learner experiment was run in this phase. No database/configuration changes or accounts were created.

**23 of 24 phases complete; one remains. Next: Phase 24 — final evidence and presentation update.** Existing PPT/notes remain unchanged until that phase. Mock publication gates and all stated feature/research deferrals remain in effect.

## Phase 24 — final evidence and presentation update

- [Final presentation](../Adaptive_MCQ_Final_Review_Phase24_Final.pptx), [slide content/notes](../Presentation_Content_and_Speaker_Notes_Phase24.md), [speaking/viva guide](../Viva_and_Review_Guide_Phase24.md) and [evidence register](../Final_Review_Evidence_Register.md).
- [Completion report](docs/phase-24-completion.md) records artifact checks and the final handover boundary. Actual UI screenshots are labelled synthetic; no AI accuracy or learner result is fabricated.

**24 of 24 roadmap phases complete.** Mock AI and all stated feature/research deferrals remain. No new application tests, model inference or database changes were performed in this final artifact phase.
