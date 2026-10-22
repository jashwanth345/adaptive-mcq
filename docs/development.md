# Phase 1 development and validation plan

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

## Before changes

**Objective:** turn the approved master blueprint into a versioned requirements/architecture baseline with evidence of local setup readiness.

**Architecture:** one local frontend, FastAPI, PostgreSQL/pgvector and a sequential worker using Ollama generator/verifier roles. Local files hold uploads. The API owns permissions/scoring; models supply candidates/verdicts; validators and teacher review control release.

**Files created in Phase 1:**

| File | Purpose |
|---|---|
| README.md | Entry point, status and later-phase boundary |
| .gitignore | Prevent future credentials, uploads, model files and private results entering version control |
| .env.example | Document future settings without credentials or applied machine changes |
| docs/requirements.md | 30 functional and 9 non-functional requirements with acceptance scenarios |
| docs/architecture.md | Decisions, component flow, conceptual ER diagram and state/API boundaries |
| docs/readiness.md | Read-only observations, unresolved setup and benchmark protocol |
| docs/development.md | Scope, dependency classification, validation and handoff |
| docs/phase-1-completion.md | Actual delivered work and check results |

All files live in outputs/adaptive-mcq. The presentation, master blueprint and review guide are retained as earlier review artifacts. There are no generated backend/frontend placeholders pretending to be complete modules.

**Database changes:** none. Conceptual entities and relationships are documented. SQL schemas, indexes, migrations and seed fixtures belong to Phase 2.

**API changes:** none. Endpoint groups and authorization boundaries are documented. No route handlers or live server are created.

**Dependencies:** none installed for Phase 1. Local read-only checks used existing system tools. The future stack below is a selection baseline, not a working dependency lockfile.

## Future dependency classification

| Use | Planned dependency | Classification |
|---|---|---|
| Frontend | React, Vite, Tailwind CSS | FREE / OPEN SOURCE |
| Backend/contracts | Python, FastAPI, Pydantic | FREE / OPEN SOURCE |
| Data and migrations | PostgreSQL, pgvector, SQLAlchemy, Alembic | FREE / OPEN SOURCE |
| Extraction | PyMuPDF, using its AGPL option | FREE / OPEN SOURCE; retain required license/source notices |
| Embeddings | Sentence Transformers and licensed local checkpoint | FREE / OPEN SOURCE |
| Inference | Ollama and the licensed local model candidates | FREE / OPEN SOURCE |
| Math | SymPy, Python math; NumPy when necessary | FREE / OPEN SOURCE |
| Authentication | Maintained JWT and Argon2 hashing libraries, selected in auth phase | FREE / OPEN SOURCE |
| Optional RAG abstraction | LangChain only if it earns its dependency cost | FREE / OPEN SOURCE |
| Development | Git, Python, Node/npm, pgAdmin | FREE / OPEN SOURCE |
| Optional editor/account/client | VS Code free build, GitHub Free, Postman Free or free equivalent | FREE functionality only; not required runtime services |

No OPTIONAL PAID dependency is selected. Model downloads and package installation may require initial internet access; prepared operation must remain local. Supported package versions are resolved and pinned during their implementation phases, using the actual hardware/interpreter. A documentary .env file cannot enforce security by itself; its rules become tested startup validation in later code.

## Phase 1 validation

Check that every requirements row has an acceptance scenario and phase mapping; all project links resolve; no prior review artifact is changed; configuration defines separate generator/verifier roles, small context, concurrency one and cloud-disable intent; credentials are blank; example settings do not point to cloud inference/database services; runtime dependencies are classified; evidence status distinguishes reported hardware from observed measurements.

Use these checks as document/configuration review, not application tests. Frontend/backend integration, SQL migrations, security enforcement, model output and adaptive behavior are not executable in Phase 1. No tests asserting nonexistent features are written. Application tests belong with their implementation phases.

## Roadmap handoff

The existing [24-phase roadmap](../../Project_Master_Blueprint.md) remains the plan. Phase 1 establishes the baseline. Phase 2 specifies normalized schemas, foreign keys, indexes, constraints, version pinning and migrations; it should first inspect/prepare an isolated local database so existing user data is preserved. Phase 3 creates backend configuration/health/error behavior. Phase 4 adds authentication. Frontend and AI features follow their listed phases.

Before each phase, describe its objective, affected files, database/API changes, dependencies and tests. Complete that phase and report actual results. Do not silently implement the rest of the project. Model benchmark success, science thresholds and human-study design remain explicit later gates.

## Run instructions

For this phase, open README.md and the linked specifications. There is no runnable application and no need to copy .env.example into an active environment. Do not treat planned localhost URLs as deployed services. Later phases will provide tested startup commands once there is software to run.
