# Run a GitHub clone locally

This repository contains source and documentation, not the original laptop's private database or installed software. A clone needs one-time dependency and database setup. GitHub upload alone does not host the full application.

## Requirements

- Windows x64, Python 3.12, Node.js 22, npm, Git.
- PostgreSQL 18 with compatible pgvector installed. The current Windows helper expects `C:\Program Files\PostgreSQL\18\bin` and creates a separate project cluster on port 55432. See [native deployment](local-deployment.md).
- Enough storage for dependencies, local embeddings and the selected small model. Inference is CPU-only and requires at least 1.5 GiB **available**, not total, RAM before each call.
- Initial downloads require internet. Prepared inference and application storage are local; no paid API or subscription is required.

The dependency lock targets Windows/Python 3.12, including a CPU PyTorch wheel. Linux/macOS need adapted and verified dependency/deployment instructions; do not assume the Windows shortcuts work there.

## Fresh installation only

Clone this repository, open PowerShell in its root folder, then run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m backend.prepare_embeddings
```

After PostgreSQL/pgvector are installed, initialize **only a new empty project installation**:

```powershell
.\.venv\Scripts\python.exe -m deployment.native init
```

This creates the dedicated database, applies migrations/grants and generates private local credentials. It refuses existing `.env` or native state. Never overwrite a working `.env`, delete a database directory to force initialization, or upload credentials. For an existing database use the [operator guide](local-deployment.md).

Run `Start-Project.cmd`, wait for Ready, then open `http://localhost:5173`. Register your own Teacher or Student account. There are no shared login credentials. New accounts correctly start with empty data. The API documentation is at `http://127.0.0.1:8000/docs`.

## Local AI preparation

Mock mode is useful for interface tests only. It cannot publish placeholder questions. To prepare the currently supported small local candidate:

1. Prepare the exact tokenizer: `.\.venv\Scripts\python.exe -m backend.prepare_generator`.
2. Obtain the official Windows Ollama runtime from its official release page and place `ollama.exe` and its required CPU libraries under `tools/ollama/`. Do not commit these binaries. The tested runtime was 0.40.0; the complete distribution can be much larger than the model itself. Do not install additional GPU packages or models merely to run the CPU demonstration.
3. Start `.\.venv\Scripts\python.exe -m backend.run_ollama`. This configures the project model directory, localhost-only service, cloud-disabled and CPU-only operation.
4. In a second PowerShell window, set `$env:OLLAMA_HOST='127.0.0.1:11434'`, then run `.\tools\ollama\ollama.exe pull qwen2.5:0.5b-instruct-q4_K_M`. This downloads approximately 398 MB of model files, with no paid account or inference API.
5. Stop the preparation runtime with Ctrl+C. Use `Start-Project.cmd` or `Start-Local-AI.cmd`; do not start two copies. The normal launcher detects the prepared manifest and selects local AI.

The exact model choice remains **Hardware-validated model selection: pending**. Both roles currently use the same small checkpoint sequentially with separate prompts; this is not independently trained-model verification. There is no guaranteed educational accuracy. No cloud fallback is used.

## Test a complete classroom flow

1. Teacher: upload a factual PDF and inspect the extracted text/OCR.
2. Generate MCQs: choose the PDF, topic and **10** questions first. If readiness is blocked, resolve its actual RAM/runtime/model error. A short document may not support 10 distinct questions.
3. Inspect source quotations, generated options, answer verification and validation. Teacher review and approval remain required; failed checks are not bypassed.
4. Assessments: enter a title, **Create a course here → Create and select course**, and choose eligible questions. Save; allow registered students; publish and share the reference code.
5. Student: join, answer, submit, inspect released results and send feedback. Teacher: inspect feedback and analytics.

The classroom UI flow has automated tests using labelled synthetic approved questions. Real PDF-to-LLM-to-approved-assessment acceptance is still pending on the development laptop because free RAM is insufficient. See [the evidence and limits](local-ai-fix-verification.md).

## Tests

Install development requirements and test dependencies separately:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm.cmd ci --prefix database/tests
$env:MCQ_RUN_DB_TESTS='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
npm.cmd test --prefix frontend -- --maxWorkers=1
npm.cmd run build --prefix frontend
npm.cmd test --prefix database/tests
$env:E2E_LIGHTWEIGHT='1'
node frontend/tests/integration-e2e.mjs
```

Run test stages sequentially on low-RAM computers. Browser tests require an installed compatible Chrome/Edge. Tests create disposable fixture data and do not establish AI quality. Do not publish test scores as research findings.
