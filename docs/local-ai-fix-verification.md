# Local AI activation and assessment fixes

Updated 17 October 2026.

## Outcome

The website now starts in **local_ollama** mode when the installed small model is present. The local startup was exercised successfully: frontend HTTP 200; PostgreSQL, schema, pgvector, runtime role and authentication permissions ready. No cloud inference, paid API or larger model was introduced. Existing accounts, uploaded PDFs and questions were preserved.

**Actual MCQ generation is still unverified and memory-blocked.** After the browser tests exited, the bounded generation trial saw approximately 1.0 GiB free RAM and returned `GENERATOR_LOW_MEMORY`. With the website running, the final snapshot showed 0.70 GiB available. The application requires at least 1.5 GiB before loading this model. No inference call bypassed that check. Ollama reported no models loaded at the final check. This is an incomplete hardware trial, not a successful end-to-end MCQ-generation result.

## Installed model

- Model: `qwen2.5:0.5b-instruct-q4_K_M` — FREE / OPEN SOURCE.
- Installed size reported by Ollama: 397,821,319 bytes.
- Digest: `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`.
- CPU-only; two inference threads; one loaded model; sequential generator/verifier calls; unload requested after each inference.
- Same checkpoint in both roles. This does not establish independent-model verification or reliable educational quality.
- **Hardware-validated model selection: pending.**

## Changes

1. The normal startup shortcut selects the prepared local AI runtime rather than always reopening mock mode.
2. Low memory no longer blocks login or the website itself. The inference guard remains enforced. Generate MCQs displays available RAM, allows settings selection, and rechecks readiness every 15 seconds while unavailable.
3. The assessment form can create and automatically select a course without navigating away or losing its title. Missing course/question selections are explained beside Save. Mock questions remain clearly labelled and cannot be published.
4. Course and release-policy selectors have full-width styling matching the form.
5. RAG caches up to 32 small query vectors, scoped by owner, model, revision and query hash. It still queries current database passages and checks material ownership/indexing on every search. Repeated topics no longer reload the embedding model for every question.
6. Native startup hands stale PID-marker recovery to PostgreSQL's own checks. It does not delete the marker or take over another database.

## Evidence

| Check | Observed result | Scope |
|---|---|---|
| Real local Sentence Transformer | Passed: three 384-dimensional vectors | Real embedding inference, not a complete uploaded-PDF/LLM test |
| Related versus unrelated diagnostic sentences | Cosine similarity 0.5808 versus -0.0098 | Diagnostic examples only; not accuracy statistics |
| Embedding diagnostic duration | 109.97 seconds | One cold run on this laptop, not a benchmark |
| Focused backend regression | 60 passed, 1 skipped | Generator/verifier contracts, RAG SQL/ownership/cache, teacher signup and batching; synthetic inference where applicable |
| Startup regression | 3 passed | Low-memory UI startup, stale marker, foreign database refusal |
| Frontend full regression before inline course addition | 124 passed | All 15 frontend test files |
| Affected frontend tests after inline course addition | 20 passed | Assessment and generation tests, including new inline course creation |
| Production frontend build | Passed | Final build includes inline course creation |
| Browser classroom journey | 14 passed | Includes inline course creation, Save, publication, student attempts, feedback, quarantine and analytics; synthetic approved questions |
| Python lint | Passed | Changed Python files |
| Native local-AI startup and live readiness | Passed | Website/backend/database/runtime available; model still unloaded |
| Actual generator and answer verifier | Blocked | Free RAM below inference guard; no real MCQ was produced |

Logs are in `logs/current-ai-tests.log`, `logs/current-ui-fixes.log`, `logs/current-frontend-tests.log`, `logs/current-frontend-build.log`, `logs/current-classroom.log`, `logs/real-rag-check.json`, `logs/real-local-ai-check.json` and `logs/current-live-readiness.json`. Earlier restricted test attempts stalled on local worker/socket startup; the successful browser and affected-UI runs used local process access. No automatic approval rejection prevented the work.

## How to use the fixes

1. Open `http://localhost:5173/`. For later sessions, double-click `Start-Project.cmd` in the project folder. Do not start multiple copies.
2. Sign in as a teacher. In Assessments, choose **Create assessment → Create a course here**. Enter a subject name, then **Create and select course**. Enter the assessment title and select questions to enable Save.
3. Old excerpt/placeholder questions remain test records. They do not become real MCQs when the startup mode changes and cannot be published.
4. In Study materials, upload a PDF and inspect its extracted text. In Generate MCQs, select that PDF, a topic, and 10 questions first. Wait for local readiness. The app automatically indexes the PDF for semantic retrieval before generation.
5. If the RAM notice remains, a fresh Windows session with only this project and one browser tab may provide more room; this is not guaranteed. The installed model does not need downloading again. The website rechecks readiness automatically. Do not force model loading under the current severe memory pressure.
6. Once ready, generate and inspect every question, exact source quotation, answer verification and validation result before teacher approval. Generation and verification quality still require this real trial. Requesting 10–30 questions does not guarantee a short PDF contains enough distinct evidence.

The bounded diagnostic can be rerun while the local runtime is running using `.venv/Scripts/python.exe -m backend.check_local_ai`. It checks real generation and two verifier stages against a clearly labelled synthetic source, writes no database records, downloads nothing, and respects the same RAM guard. It does not replace a full PDF-to-assessment acceptance test.
