# Setup and quick start

This guide covers the prepared Windows laptop and a separate fresh-machine setup. The primary target is one computer. No paid API, subscription, credit card, hosted database or cloud storage is required. Initial installation needs downloads; routine prepared startup does not download packages or models.

## This laptop: already configured

Project folder: `C:\Users\user\Documents\Codex\2026-10-05\important-additional-task-before-beginning-the\outputs\adaptive-mcq`.

1. Open [Start-Project.cmd](../Start-Project.cmd). Keep its terminal open and wait for **Ready**.
2. Open **http://localhost:5173** in the browser.
3. For a teacher account, choose **Sign up → Account type → Teacher** on the website. Enter your own email, display name and private password. The optional [Create-Teacher.cmd](../Create-Teacher.cmd) operator flow remains available. Passwords must be 12–128 characters. No shared teacher login is supplied. Reuse your existing account on subsequent visits.
4. Students choose **Create student account**, register, then sign in. Registration creates only the student role. An email identifies a local account; the system does not send verification mail.
5. Follow the [user guide](user-guide.md). A new database correctly shows empty courses, materials, assessments and analytics.
6. Stop the website with **Ctrl+C** in its terminal. Then run [Stop-Database.cmd](../Stop-Database.cmd) if you also want to stop the project database. Stopping does not delete saved work.

Refreshing or closing a page requires signing in again because browser tokens are held only in memory. Saved server records remain. Save attempt progress before leaving a page.

| Local component | Address / storage |
|---|---|
| Website | `http://localhost:5173` |
| Backend and API documentation | `http://127.0.0.1:8000` and `/docs` |
| Project database | `127.0.0.1:55432`, database `adaptive_mcq` |
| PDF files | `backend/uploads/` |
| Private application configuration | `.env` |
| Private database operator state | `data/native-postgres/` |
| Operator backup bundles | `backups/` |

The stack uses one backend worker. `Start-Project.cmd` now starts local Ollama when the prepared small model manifest exists; otherwise it uses the configured demonstration mode. Mock mode does not produce educational MCQs. The local MiniLM embedding snapshot is separate; semantic indexing/search loads it only when requested. See [the current AI readiness report](local-ai-fix-verification.md). Do not start a second Ollama runtime while the launcher is running.

## Check readiness without starting the website

From a PowerShell terminal in the project folder:

```powershell
.\.venv\Scripts\python.exe -m deployment.native start
.\.venv\Scripts\python.exe -m deployment.local doctor
```

Run `doctor` with the website stopped: occupied website ports are intentionally a failure. A passing report checks startup prerequisites, including local embedding-file hashes, without loading a model. It does not measure AI correctness. For a failure, use [troubleshooting](troubleshooting.md).

Private credentials have already been generated. Do not copy `.env.example` over `.env`, rerun initialization, regenerate secrets, reinstall packages, or run migration/grant scripts as everyday startup steps. Never paste `.env` or `operator.json` into messages, screenshots or a college submission.

## Fresh Windows machine: operator preparation

This path is for another empty installation, not the prepared laptop. It is documented from the existing setup tooling; it has not been independently replayed on a second computer. Existing 8 GB hardware is sufficient for the tested lightweight website checks, not a certified full-stack AI memory budget.

1. Copy reviewed project source, lockfiles and documentation to a writable folder. Exclude `.env`, `data`, uploads, backups, logs, generated evaluation runs, `.venv` and `node_modules`. Transfer actual private records only using the [backup/restore process](local-deployment.md), not a copied live database directory.
2. Prepare Windows x64, **Python 3.12** (tested environment 3.12.14), Node.js **22.19.0**, npm **10.9.3**, and compatible **PostgreSQL 18.x** (tested 18.4). The Python lock includes a Windows CPython 3.12 CPU-only PyTorch wheel; another OS/interpreter needs a deliberately adapted and tested lock. These are recorded versions, not claims about the newest releases.
3. Install compatible pgvector using the [native prerequisites](local-deployment.md). This project's convenience helper expects PostgreSQL at `C:\Program Files\PostgreSQL\18\bin`, port 55432 and its dedicated folder. Confirm those assumptions before using it. Never overwrite an unrelated service or cluster.
4. Prepare the Python environment and frontend once:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
npm.cmd run build --prefix frontend
```

5. Prepare the pinned local embedding snapshot once, or transfer the intact prepared snapshot with its manifest and verify it. This is an embedding-model download, not a generator LLM download:

```powershell
.\.venv\Scripts\python.exe -m backend.prepare_embeddings
```

6. Choose **one** database configuration path. For an empty installation matching the helper assumptions, `deployment.native init` initializes its dedicated cluster, roles, extension, all migrations/grants and private `.env`. It refuses existing state; if interrupted, inspect the operator log instead of deleting state and retrying blindly. Alternatively, a qualified operator follows the manual database setup and `deployment.local configure` in the [deployment guide](local-deployment.md). Do not combine both paths.

```powershell
.\.venv\Scripts\python.exe -m deployment.native init
.\.venv\Scripts\python.exe -m deployment.local doctor
```

7. First verify the lightweight website with `GENERATOR_MODE=mock`, `VERIFIER_MODE=mock`. For real local AI, follow [the explicit small-model preparation](github-setup.md#local-ai-preparation), including the tokenizer and local-only runtime. Hardware and educational-quality validation remain pending. Back up before importing retained records.

For source development/testing, install `backend/requirements-dev.txt` in the same environment and use the maintainer guide. These installs are unnecessary on the prepared laptop.

## Cost and license classification

| Selected technology | Classification and use |
|---|---|
| React, Vite, Tailwind, TypeScript, Node/npm | FREE / OPEN SOURCE; local frontend/toolchain |
| Python, FastAPI, Pydantic, Uvicorn, psycopg, SQLAlchemy | FREE / OPEN SOURCE; backend/contracts/database access |
| PostgreSQL, pgvector | FREE / OPEN SOURCE; relational and vector data |
| PyMuPDF | FREE / OPEN SOURCE under its AGPL option; retain applicable notices/source obligations |
| Sentence Transformers, CPU PyTorch, pinned MiniLM | FREE / OPEN SOURCE; local embeddings |
| PyJWT, Argon2 components | FREE / OPEN SOURCE; local authentication |
| Python arithmetic; installed SymPy dependency | FREE / OPEN SOURCE; active validation uses bounded exact arithmetic, not general symbolic proof |
| Ollama and candidate Qwen adapter | FREE / OPEN SOURCE; optional future local inference, currently disabled/unvalidated |
| Git | FREE / OPEN SOURCE; optional source versioning |
| Microsoft C++ Build Tools | FREE proprietary build-time tool used to compile pgvector; not an application service |

No OPTIONAL PAID component is required or selected. The service/subscription target is **₹0**; existing hardware, electricity and internet access are not included in that claim. GitHub Free, VS Code and Postman are optional development conveniences, not runtime dependencies. LangChain, Docker and cloud hosting are not required. Installed transitive dependencies are listed in the lockfiles; distribution should retain their notices. This guide is not a license audit.
