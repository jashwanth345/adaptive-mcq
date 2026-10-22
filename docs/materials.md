# Private PDF materials — Phase 8

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Phase 9 adds [local embeddings and page-cited retrieval](rag.md) on top of this ingestion release. Statements below about embeddings/retrieval being planned describe the Phase 8 boundary; the Phase 9 guide supersedes that status. OCR and pasted-text input remain planned.

Teachers and students share the **Study materials** screen. Upload a text PDF, give it a title, inspect page-linked extracted passages and browse your saved documents. Documents are private to the authenticated owner. Classroom membership does not grant access to another user's uploads. There is no public/static PDF route, cloud storage, OCR or model call.

## Local setup

Use the existing backend, frontend and authentication setup. Install the updated backend lockfile inside the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

After applying the existing migrations and auth/teacher/student grants, a trusted PostgreSQL operator applies the new permissions against the same application database:

```powershell
psql -h 127.0.0.1 -U YOUR_DATABASE_OPERATOR -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f database/material_runtime_grants.sql
```

Replace the operator placeholder with your own configured operator account. No password or real account is supplied. The runtime role receives SELECT and restricted column INSERT on materials/documents/chunks, never UPDATE/DELETE of immutable provenance. The backend enforces per-user ownership; this is not per-user database RLS. Database readiness still reports the foundation/auth checks, not feature-specific material grants. Missing material permissions produce a safe 503.

Start the usual single-worker backend and frontend. The backend creates `backend/uploads/` on first upload. Files use random hexadecimal `.pdf` names and are outside frontend/static directories. Original client filenames are never used for filesystem paths. Back up uploads together with PostgreSQL. Protect the local OS account: application ownership does not encrypt files from other people who can access that OS account.

PyMuPDF **1.28.2** is the sole added dependency, **FREE / OPEN SOURCE**, selected under its AGPL option. No commercial PyMuPDF product is used. Keep applicable notices/source obligations when distributing this project. [Official licensing](https://github.com/pymupdf/PyMuPDF), [text extraction documentation](https://pymupdf.readthedocs.io/en/latest/recipes-text.html).

## API and processing

All routes need a valid bearer session with a current teacher or student role. Responses are `no-store`; unauthorized IDs return the same 404 as absent IDs. Filenames, owner IDs, internal document IDs and hashes are omitted from preview responses.

| Route | Contract |
|---|---|
| GET `/api/v1/materials?offset=0&limit=6` | Owner's processed, nonarchived version-1 materials; max page size 24 |
| POST `/api/v1/materials?title=...` | Raw binary body with `Content-Type: application/pdf`; URL-encoded title, 1–250 characters; returns 201 `{id,reused}` only after processing/save |
| GET `/api/v1/materials/{id}?page=1` | Owned material metadata, passages for that page, and page numbers with no extractable text |

POST validates auth before consuming the request stream. Title is metadata; it is never a path. No multipart dependency is needed. The frontend sends the File directly, with the existing memory-only bearer token. Upload client timeout is 60 seconds; normal API requests retain 15 seconds. Title query strings are excluded from backend access logs. Same-owner SHA-256 duplicate bytes reuse the existing record and original title; another owner can store an independent private copy. A lost response can be retried without adding a duplicate.

Limits: 5 MiB per PDF; 100 pages; 40,000 cleaned characters per page; 200,000 per document; 15-second upload stream deadline; 30-second extraction subprocess timeout; one active upload/extraction per API process; 50 stored documents or 100 MiB per owner, including archived records. Run the supported one-worker launcher. These are operational defaults, not experimentally validated optimum thresholds. Parsing a single compressed page may allocate memory before the text-size check; subprocess/time limits are not a hard memory sandbox. Hostile-PDF sandboxing and hard process-memory limits are future security hardening. This release is a trusted local college demonstrator, not a public upload service.

The worker reads text with PyMuPDF's sorted text extraction, removes control characters, normalizes Unicode to NFC and normalizes horizontal whitespace. It preserves page numbers, words and line breaks; it does not claim to reconstruct complex tables, columns or equations perfectly. No document JavaScript, generated code or external URLs are executed. Review extraction against the original PDF. Extracted text is untrusted source data, rendered as plain React text; it must remain untrusted when Phase 9 builds model prompts.

Chunks contain at most 1,200 characters, overlap by up to 120 characters within the same page, never cross pages, and have SHA-256 hashes, ordered ordinals and splitter version `page-char-1200-overlap-120-v1`. `token_count` currently stores a conservative UTF-8 byte-count estimate, **not measured tokenizer output**. Phase 9 must recompute context lengths with the actual embedding/model tokenizer; it must not use this estimate as a claimed token measurement. There are no vectors yet.

Image-only/blank documents return `PDF_NO_TEXT`; encrypted PDFs return `ENCRYPTED_PDF`; invalid PDFs return `INVALID_PDF`. Mixed PDFs are accepted if some text exists; empty pages are listed visibly and remain in page numbering. OCR is not silently substituted. Page, size and timeout failures have separate UI messages. Unsupported or rejected PDFs are not retained as successfully processed materials.

## Failure and recovery

Successful ingestion writes material, immutable document/chunks and audit event in one transaction. The file already exists before commit. Ordinary validation, extraction, quota and duplicate paths remove their temporary upload; the processing gate is released even if cleanup fails. A crash, disk cleanup failure or uncertain database commit can leave an unreferenced `.pdf`. On SQLAlchemy database errors the file is deliberately retained because a dropped connection can hide a successful commit.

Operator recovery: stop the backend so no uploads are active; back up database and uploads; compare filenames in `backend/uploads/` with `SELECT storage_key FROM mcq.documents`. Investigate missing referenced files and restore them from backup. Only files positively confirmed unreferenced should be removed manually. Never remove a file simply because the UI reported a connection failure. No automatic deletion or recovery claim is made in this phase.

This bounded synchronous 201 flow deliberately replaces the blueprint's provisional 202/job proposal for the current small local ingestion release. It neither queues work nor promises crash-resumable jobs. Persistent ingest jobs, version replacement/reprocessing, archive/deletion with retention rules, pasted-text entry, OCR and course-material sharing remain planned. The PDF portion of requirement R03 is implemented; its pasted-text portion remains open. Phase 9 covers local embeddings and retrieval.

## Verification

Synthetic PDFs/accounts are test fixtures, not research evaluation data. Backend integration uses the disposable PostgreSQL/pgvector adapter and actual restricted SQL roles. It does not establish native PostgreSQL password authentication or multi-connection concurrency guarantees. Browser fixtures override only the upload directory to temporary storage; application production storage receives no test files.

From the project root:

```powershell
$env:MCQ_RUN_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -p no:cacheprovider
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

Use a fresh writable `--basetemp` if Windows sandbox identities prevent access to an older pytest directory. Real browser tests need locally installed Chrome/Edge and use temporary API/frontend ports. Native PostgreSQL/pgvector configuration remains a deployment prerequisite; Phase 8 does not silently install or modify a real database.
