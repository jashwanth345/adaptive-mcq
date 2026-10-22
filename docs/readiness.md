# Hardware and dependency readiness

**Latest update, 15 October 2026:** [Phase 22](phase-22-completion.md) installed the approved free C++ build tools and pgvector 0.8.7 for PostgreSQL 18.4, configured the dedicated native project database and passed local startup/application recovery acceptance. The application uses lightweight test generation and advisory reviews; real generator/verifier inference and hardware-validated model selection remain pending. The current adapter candidate is the small Qwen tag for both roles, with no claim of independent-model verification; no LLM was downloaded or run. See [Phase 10 hardware evidence](phase-10-hardware.md) and the [Phase 11 verifier guide](verifier.md). The following Phase 1 and Phase 9 observations are historical, not the current installation inventory.

Read-only check performed 5 October 2026 in the attached local Windows workspace. This report establishes planning readiness only. No packages, models, database objects, services, environment variables or firewall rules were changed.

## Reported versus observed

| Item | Evidence | Status |
|---|---|---|
| Laptop | User reports Dell Inspiron 14 3000 | Reported, not independently re-verified |
| CPU | User reports Intel Core i5-1035G1 @ 1.00 GHz | Reported |
| RAM | User reports 8 GB DDR4 | Reported |
| GPU | User reports Intel UHD; no dedicated GPU/VRAM | Plan CPU inference; shared memory adds no RAM |
| OS | Local API reports NT 10.0.26300.0, 64-bit | Observed build; Windows edition/product label not verified |
| Workspace drive C: | Approximately 60.5 GiB free of 237.13 GiB | Observed snapshot, can change |
| Detailed hardware query | Windows CIM access unavailable | No verified idle RAM, total hardware inventory or CPU benchmark |
| Windows services | Service Control Manager access unavailable | Cannot assert service installed/running/stopped from that query |

The attached machine's model/CPU could not be independently compared with the reported laptop. Keep the user's 8 GB specification as the conservative deployment target. Disk findings refer to this workspace's C: drive; recheck the actual installation/model target if a different computer or drive is used.

## Software found

| Component | Observation | Consequence |
|---|---|---|
| Python | 3.13.1 at the user's normal Python installation | Interpreter exists; ML wheel compatibility and virtual environment remain untested |
| Node.js | 22.19.0 | Meets currently documented Vite Node 22.12+ branch requirement |
| npm | 10.9.3 | Package manager exists; no packages installed |
| Git | 2.54.0.windows.1 | Available; no repo initialization, commit or remote created |
| PostgreSQL client | 18.4 under C:/Program Files/PostgreSQL/18/bin | Present outside PATH; use explicit path or deliberately configure it later |
| Default PostgreSQL connection | pg_isready: no response at 127.0.0.1:5432 | No default-port server response during check; another port/cluster is not ruled out |
| pgvector | vector.control and vector.dll absent from the inspected PostgreSQL 18 locations | Not available in that installation based on filesystem check; SQL extension availability untested |
| Ollama | Not found on PATH or at default per-user executable location | Local runtime readiness unconfirmed; other custom installations not ruled out |
| LLM and embedding checkpoints | No inventory/benchmark performed | Not downloaded or validated by this task |

Python 3.13 is not automatically rejected or declared compatible with all planned ML libraries. Later installation must resolve a tested package set in a project virtual environment. If required CPU wheels are unavailable, select a supported free Python version explicitly rather than changing the user's existing installation blindly.

Sources for current compatibility: [Vite installation guide](https://vite.dev/guide/), [Ollama Windows requirements](https://docs.ollama.com/windows), [pgvector Windows installation](https://github.com/pgvector/pgvector#windows). Reviewed 5 October 2026. Vite templates may impose additional requirements. Ollama's documented minimum is Windows 10 22H2 or newer. pgvector's native Windows build route needs matching PostgreSQL development files and C++ build support; the actual route is not installed or tested in this phase.

## Hardware-validated model selection

**Pending actual execution and quality benchmark.** This heading describes the selection gate, not a completed result.

| Candidate | Purpose | Classification | Status |
|---|---|---|---|
| qwen2.5:1.5b-instruct-q4_K_M | Generator | FREE / OPEN SOURCE candidate | Not installed or benchmarked by this phase |
| smollm2:1.7b-instruct-q4_K_M | Verifier | FREE / OPEN SOURCE candidate | Not installed or benchmarked by this phase |
| sentence-transformers/all-MiniLM-L6-v2 | Local embeddings | FREE / OPEN SOURCE candidate | Dependency/model execution untested |

The [existing blueprint](../../Project_Master_Blueprint.md) records official model/license sources and the reasoning for these candidates. Recheck exact tags/digests before installation. Neither Gemini API names nor their free quotas meet the local-checkpoint requirement.

## Pre-installation decisions

1. Confirm the Windows product/version and actual deployment laptop match the reported target.
2. Recheck free storage on package, database, model and upload drives. Keep space for installers, wheels, extracted libraries, model files, database growth and backups. A model file's size is not its runtime RAM footprint.
3. Inspect the existing PostgreSQL installation/cluster configuration using permitted methods before creating or starting anything. Do not overwrite an existing database or initialize over an existing data directory.
4. Select a reproducible local pgvector installation route compatible with PostgreSQL 18.4, or document a justified separate local version. Avoid untrusted extension binaries and avoid making Docker mandatory on 8 GB RAM.
5. Install/configure Ollama locally in the relevant later phase with cloud disabled. Starting the existing app requires its own effective environment; project .env text alone is insufficient.
6. Create isolated dependency environments and pin the actually installed versions. No model training or large-model downloads are planned.

## Benchmark protocol, planned

Run after local runtime/model setup, with explicit result records. Begin with a small authorized English concept corpus and supported arithmetic fixtures. Check one generator call and one verifier call separately before the full stack. Use single residency and small context. After basic feasibility, run repeated matched tasks with PostgreSQL/backend/browser active; measure cold-load and warm-inference time, total memory, paging, failures and structured-output validity.

Record model tag/digest, quantization, source/prompt revisions, context/output limits, actual hardware and response timings. Include invalid candidates: missing correct option, two equivalent correct options, unsupported claim and misleading explanation. Include valid candidates to reveal false rejection. Independent human review determines gold labels.

Do not declare hardware validation passed on a single successful prompt. Require the full stack to remain responsive without memory exhaustion, measure available capacity, and review item-quality errors. The maximum tolerable wait and quality thresholds must be fixed in the benchmark protocol before final selection. There is no measured throughput, memory claim, accuracy or acceptance result yet. If quality is inadequate, revise scope/model pairing within local constraints instead of disabling checks.
## Phase 9 local embedding readiness

As of 7 October 2026, the project environment contains CPU-only PyTorch and Sentence Transformers, with a pinned all-MiniLM-L6-v2 snapshot under `models/`. Real offline CPU embedding and browser-to-pgvector retrieval have been exercised using disposable database/PDF fixtures. This establishes functional embedding/retrieval operation only, not a sustained RAM/latency benchmark, MCQ quality result or generator/verifier hardware validation. Native PostgreSQL/pgvector installation/authentication remains pending. See [rag.md](rag.md) and the Phase 9 completion record for boundaries and setup.
