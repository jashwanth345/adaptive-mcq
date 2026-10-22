# Phase 8 — PDF upload and processing

Objective: teachers and students can upload a private text PDF, inspect extracted page text, and retain page-linked chunks for Phase 9. No LLM or embedding is invoked.

Files: backend `materials/` extraction/service/routes/schemas; shared frontend Materials screen; existing router/client integration; runtime grants; focused backend/frontend/browser tests and documentation.

Architecture: authenticated raw PDF upload → bounded local temporary file → one isolated extraction subprocess → atomic material/document/chunk/audit database transaction → owner-only paginated library and page preview. The small local release uses a synchronous bounded request (201), a deliberate refinement of the blueprint's proposed 202 persistent ingestion job. Durable background ingestion/reprocessing remains planned; no background work is lost silently because no work is acknowledged before completion.

Database: reuse existing materials/documents/chunks; no migration changes. Add explicit SELECT/INSERT grants. Immutable chunks carry page numbers, SHA-256, splitter version and a conservative token estimate, not an actual model token count. Exact token budgeting belongs to Phase 9.

API: GET/POST `/api/v1/materials`, GET `/api/v1/materials/{id}?page=1`. POST uses application/pdf with a validated title query parameter, avoiding multipart buffering and client filenames. Auth is checked before streaming. Max 5 MiB, 100 pages, 40,000 extracted characters/page, 200,000/document, 30-second extraction timeout, 15-second body timeout, one active ingestion per API process; run one backend worker. Owner quota: 50 documents / 100 MiB. Duplicate bytes for the same owner reuse the existing material.

Dependency: PyMuPDF, FREE / OPEN SOURCE (AGPL option). No paid services or new frontend package. Image-only/encrypted/invalid PDFs receive explicit errors; mixed documents retain page numbering and warn about empty pages. OCR, pasted-text input, replacement versions, archive/deletion, durable ingestion jobs, embeddings and retrieval remain separate work.

Tests: real generated text PDFs, page boundaries/hashes, encrypted/invalid/no-text inputs, upload caps, busy/timeout/error cleanup, duplicate/private ownership, runtime grants, UI pending/error/preview states, actual browser upload on desktop/mobile. No experimental performance or accuracy claims.
