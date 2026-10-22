# Phase 8 completion — PDF upload and processing

Completed 6 October 2026, following the user's explicit Phase 8 instruction.

## Delivered

- Shared teacher/student **Study materials** screen: private upload, real stored library, loading/error/retry states, duplicate notification, page navigation and text previews, including mobile layout.
- Authenticated raw-PDF API with streamed size checks, generated filenames, bounded sequential extraction, owner-scoped access and safe errors. No remote service or LLM call.
- PyMuPDF 1.28.2, FREE / OPEN SOURCE (AGPL selection), pinned in the existing backend dependency lockfile.
- Existing material/document/chunk tables reused. Page-linked passages, hashes, immutable provenance and audit event persist together. New restricted runtime grant script; no migration modification.
- Explicit invalid/encrypted/image-only PDF handling and warnings for pages without text. Duplicate bytes reuse the same owner's record. Ordinary failures clean temporary uploads; uncertain database commits preserve files for documented reconciliation.
- [Setup, API, limits and recovery guide](materials.md), [phase plan](phase-8-plan.md), updated project README/frontend guide, and tests.

## Verified results

| Check | Actual result |
|---|---|
| Complete backend suite with database tests enabled | **106 passed**, no skipped tests; one existing Starlette HTTPX deprecation warning |
| Complete frontend suite | **46 passed** across five files |
| Real-browser suite | **24 checks passed** against the real backend and disposable PostgreSQL fixture |
| TypeScript + production build | Passed; build refreshed after teacher workflow status wording update |
| Backend Ruff and dependency consistency | Passed |
| Desktop/mobile visual review | Inspected 1440px desktop and 390px mobile materials screens; no horizontal page overflow |
| Attached MCQGen paper extraction smoke check | 13 pages, 61 chunks, no pages without extracted text; no application upload was retained |

The paper smoke check confirms extraction completed, not reading-order correctness, semantic accuracy, question quality, latency or learning outcomes. Screenshots use synthetic accounts and short generated study PDFs, clearly development evidence rather than project evaluation results.

Backend checks include real extraction subprocesses, private access between students and teacher-only accounts, persisted source-page previews, duplicate handling, malformed/blank/encrypted/over-page PDFs, size caps, busy handling, timeout/crash mapping, safe text rendering, cleanup and restricted SQL privileges. The full suite also rechecks prior authentication, course and student behavior. The first frontend attempt exposed a file-input fixture incompatibility and one worker startup timeout; the final full run passed after using the file input's selected File directly. No tests were disabled.

Logs relative to the surrounding workspace:

- `work/phase8-backend-tests.log`
- `work/phase8-frontend-final.log`
- `work/phase8-browser-final.log`
- `work/phase8-build-delivery.log`
- `work/phase8-browser-final/materials-desktop.png`
- `work/phase8-browser-final/materials-mobile.png`

## Remaining boundaries

Native PostgreSQL/pgvector setup, password authentication and real concurrent database sessions remain unverified. Test execution used the documented disposable PostgreSQL/pgvector adapter with explicitly restricted SQL roles. No native data, real user credentials, active `.env` or production upload folder was created. Apply the material grant script as the trusted operator before native use.

This phase intentionally uses bounded synchronous 201 ingestion, not the blueprint's provisional durable 202 job design. No crash-resumable worker is claimed. Operational byte/page/text limits and a subprocess timeout are not a hard parser-memory sandbox; public hostile-upload deployment requires later hardening.

PDF ingestion is complete for this phase. The pasted-text portion of R03 remains open, alongside OCR, replacement versions, archive/deletion, source sharing and durable ingestion jobs. Token counts are conservative byte estimates until Phase 9 supplies actual tokenizer budgeting. RAG embeddings/retrieval, dual LLMs, mathematical validation, assessments and adaptive learning remain planned. Hardware-validated model selection is still pending.

Next roadmap phase: **Phase 9 — local RAG pipeline**. No Phase 9 implementation was started.
