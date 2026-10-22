# Teacher signup and 10–30-question generation

Updated 17 October 2026. This update follows the frontend refresh.

## What was wrong

Uploading a PDF extracted and saved its text, but the application was deliberately running a **mock generator**. Its excerpt and placeholder distractors are not educational MCQs. The previous form supported only one draft, and public registration only created students. Passing workflow tests did not mean a real LLM had been installed or evaluated.

## What changed

- Signup now has an **Account type** selector: Student or Teacher. Both use the same login. The server opens the correct dashboard from the stored role.
- Teacher signup creates a new teacher's own workspace. Re-registering an existing student email cannot promote that account. Existing records and role restrictions are preserved.
- **Number of questions** offers every integer from 10 to 30. The real-AI flow prepares the PDF for search, retrieves evidence, generates one draft, verifies it, validates it, saves progress and then proceeds to the next question.
- A question set shows how many drafts were saved and which passed the checks. A rejected/uncertain question is not silently counted as an approved MCQ. A short or unsuitable PDF may not support the requested number of distinct questions.
- Generation rotates relevant passages and includes recent question stems in the prompt. Exact repeated stems in a batch are rejected before saving; the existing validation stage also checks similar questions.
- Transient failures retain the saved draft and reuse its action keys when retrying the same settings on the same page. **Pause after this question** finishes the current item's checks before pausing. Refreshing/signing out ends this in-memory batch controller; saved questions remain in Saved drafts. Automatic batch resumption across a new login is not implemented. Long batches can be interrupted by the existing session expiry, so begin with 10 questions.
- Semantic encoding refuses to start below 1 GiB free RAM. LLM inference requires at least 1.5 GiB free RAM. These are protective admission checks, not a promise of acceptable speed or quality.
- `Start-Project.cmd` now starts the local AI runtime when the prepared model manifest exists. `Start-Local-AI.cmd` explicitly selects this same mode. Neither shortcut downloads models or rewrites `.env`. Memory checks happen before inference, so low memory no longer prevents opening the website. Missing weights still leave the ordinary launcher in its configured demonstration mode.
- Low-memory generation displays available RAM and rechecks readiness every 15 seconds. PDF and question-count selection remain usable while waiting.
- Assessment creation now supports **Create a course here → Create and select course**. The title and question selection remain on the page. Save explains whether a course or question selection is missing. Test placeholders still cannot be published.
- Repeated topic searches reuse a bounded, owner-scoped cache of 384-dimensional query vectors. Source ownership, indexing status and current database results are checked every time. No embedding model stays loaded between requests.

## Current AI status — not yet validated

The laptop has 7.77 GiB usable RAM. The small Qwen candidate is now installed locally: 397,821,319 bytes, digest `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`. Only this small model was downloaded; no cloud inference was used. Real embedding inference succeeded on three diagnostic sentences (384 dimensions each). The LLM trial has so far been refused by the 1.5 GiB free-RAM guard, so **real MCQ generation and answer-verification quality are not yet validated**. See [the latest verification report](local-ai-fix-verification.md), rather than interpreting earlier mock test passes as real generation evidence.

Exact model selection remains **Hardware-validated model selection: pending**. The existing adapter supports the small `qwen2.5:0.5b-instruct-q4_K_M` candidate. The [Ollama model page](https://ollama.com/library/qwen2.5:0.5b-instruct-q4_K_M) lists a 398 MB Q4_K_M download; the [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) identifies Apache 2.0 licensing. Classification: **FREE / OPEN SOURCE**. It is a candidate for a bounded hardware trial, not an educational-quality recommendation already proved by experiments.

Both current roles use that same checkpoint in separate sequential calls, with different prompts and a blind-answer verification step. This is **not independently trained-model verification**. The same model may repeat its own mistakes. Generator/verifier names are configurable, but the current exact-token-budget adapter accepts only this supported checkpoint; arbitrary model substitution requires an adapter and quality evaluation. Gemini names from the earlier diagram are not local model files supported by this implementation.

## How to test now

1. Open `http://localhost:5173/register`. Select **Teacher**, enter a new email/name/password, then choose **Create teacher account**. Sign in at `/login`; the Teacher dashboard should open. Repeat with a different email and Student to test the student dashboard. An existing student keeps their role.
2. Upload a PDF in **Study materials**. Inspect the page-linked extracted text. For scans, inspect the OCR notice and correct source material if recognition is poor.
3. Continue to **Generate MCQs**. Select the document, topic, difficulty and a count between 10 and 30.
4. In mock mode, **Generate N MCQs is disabled**. **Create test draft** tests persistence and review screens only. Placeholder output is deliberately labelled and cannot be published or scored.
5. Existing feedback tests use disposable synthetic assessments. Mock drafts cannot create legitimate scored attempts, so they cannot be used to manufacture student feedback evidence. After a real question passes checks, a teacher must review it, publish an assessment and allow the student. The student joins by code, submits answers, then reports an issue from the results. Review feedback and quarantine status in Feedback review.

## How to test real local AI

The small candidate is already installed on this laptop. **Do not download it again.** Close an earlier website/runtime session, then double-click `Start-Project.cmd`. Open Generate MCQs and check the visible readiness notice. At least 1.5 GiB must be free before each model call; the app waits rather than inventing output.

For a fresh installation only, prepare the same small candidate explicitly. No model download is performed by either startup shortcut. Start the local-only Ollama runtime in one terminal:

```powershell
.\.venv\Scripts\python.exe -m backend.run_ollama
```

In a second terminal, the following **explicit preparation step downloads the small candidate once**; it is not a cloud inference call and requires no account, payment or API key:

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11434'
.\tools\ollama\ollama.exe pull qwen2.5:0.5b-instruct-q4_K_M
```

Stop that preparation runtime afterward. Close the running website supervisor before switching modes, then double-click `Start-Local-AI.cmd`. The launcher checks installed files and starts the project's database, local Ollama and website. Low memory allows the website to open but keeps inference unavailable. There is no cloud fallback.

Use a short, clean PDF with enough factual content for 10 questions. Sign in, select the document and topic, and generate **10** first. Indexing runs locally, and embedding workers exit before LLM inference. Ollama uses CPU, two inference threads, a 2,048-token context and one loaded model; each inference request asks the runtime to unload afterward. Check generation, verifier recommendations, source quotations, options and explanations manually before increasing to 20 or 30. The verifier is advisory and teacher approval remains separate. No latency or correctness claim is established until this hardware trial actually succeeds.

## Verification

Final checks: 326 unique backend checks passed across the full run and the corrected security rerun, with one real-embedding test skipped; 123 frontend tests, 120 database checks, 7 migration tests and 69 browser checks passed. See the [verification report](question-generation-verification.md) for logs and exact scope. These verify implementation behavior using synthetic inference where needed, not educational model quality.

All core inference and storage remain local. React/Vite/Tailwind, Python/FastAPI, PostgreSQL/pgvector, Sentence Transformers, Ollama, Qwen and SymPy are FREE / OPEN SOURCE. The scanned-PDF fallback uses FREE installed Windows OCR, a proprietary Windows platform feature; selectable-text PDFs do not depend on it. No paid dependency was introduced.
