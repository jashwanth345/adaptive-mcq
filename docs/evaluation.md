# Evaluation harness — Phase 19

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

The Evaluation lab and local command-line harness measure software behavior and prepare reproducible experiments. They do not establish AI reliability or educational benefit. Website runs are always **synthetic smoke checks**; no model, embedding download or cloud service is invoked. No evaluation candidate can become a classroom question. All added components use existing FREE / OPEN-SOURCE dependencies.

## Teacher workflow

Open **Evaluation lab** from teacher navigation. Run a synthetic smoke check, reopen a saved check, download its evidence and download an operator review bundle. The synthetic fixture uses two documents and two seeds: four requested slots per A/B/C/D condition, sixteen condition records and eight unique generated candidates. The fixture intentionally lets an incorrect numerical answer pass the mock verifier so the math stage can reject it. These counts test plumbing; they are not experimental results.

The page explicitly leaves AI correctness and learning outcomes **To be evaluated**. Up to twenty immutable runs are saved per teacher. Retrying the same command returns the existing run. Other teachers and students cannot read these records. The operator review bundle contains a private allocation map: extract and share only reviewer items and the blank ratings template with raters.

## Setup and endpoints

Apply all twelve migrations using the existing [database setup](database.md), then apply `database/evaluation_runtime_grants.sql` with the same `runtime_role` substitution as previous grant files. Migration 012 adds a separate immutable evaluation table and two scoped functions. It preserves questions, assessment snapshots, learner evidence and scores. No direct table privileges are added to the runtime. No native database was migrated during Phase 19 development.

| Endpoint under `/api/v1/teacher/evaluation` | Purpose |
|---|---|
| `GET /runs` | List the current teacher's saved checks |
| `POST /runs` | Run fixed mock inputs; body contains only `idempotency_key` |
| `GET /runs/{id}` | Read an owned run and summary |
| `GET /runs/{id}/review-pack` | Download operator review bundle |
| `POST /adaptive-export` | Export selected owned classroom evidence with explicit confirmation |

All endpoints require a current teacher role and use the existing authenticated, no-store API. The browser cannot request local inference. Access rules are tested on disposable PostgreSQL fixtures; native authentication and multi-connection concurrency remain separate deployment checks.

## Offline commands

Run these from the project root. Replace `RUN` with the printed directory under `evaluation/runs`. Choose fresh output directories/files: the harness never overwrites existing artifacts.

```powershell
.\.venv\Scripts\python.exe -m evaluation smoke
.\.venv\Scripts\python.exe -m evaluation review-pack evaluation/runs/RUN/run.json evaluation/runs/RUN/review
.\.venv\Scripts\python.exe -m evaluation report evaluation/runs/RUN/run.json evaluation/runs/RUN/unrated-summary.json
.\.venv\Scripts\python.exe -m evaluation template evaluation/runs/my-protocol
```

Smoke outputs contain `run.json`, `summary.json`, formula-safe `records.csv` and a completion manifest with canonical SHA-256 hashes. Runs save only after completion; interrupted computations are not resumable. Preserve the manifest and original files. Hashes detect accidental changes when compared; they are not signatures or proof against an operator rewriting artifacts. Input JSON is bounded to 20 MiB; output uses finite JSON numbers. The local runner lock rejects overlapping command-line runs.

## Matched experimental design

| Condition | Action | Interpretation |
|---|---|---|
| A | Generate from topic only | No retrieved source supplied |
| B | Generate using frozen retrieved context | Exact quote/citation integrity required for retention |
| C | Verify the exact B candidate | Independent solving prompt followed by critique; failed candidates remain recorded |
| D | Apply bounded mathematical validation to C | Unsupported arithmetic is not silently approved |

A and B use matched source/case, requested difficulty, cognitive level, type, model pair, seed and token budget. C/D reuse B's question instead of generating easier replacement questions. There are zero retries/regenerations: a REGENERATE recommendation is counted as not retained. This is a paired filtering ablation, not a benchmark of the complete production regeneration policy. B includes citation integrity, so the A/B difference is more than just prompt length. Exact quotes establish provenance, not factual truth.

The harness consumes **frozen local RAG snapshots**. It does not re-run PDF extraction, embeddings or retrieval for every condition. Record the local embedding model/revision and the exact chunks retrieved by the existing RAG pipeline. Retrieval quality, latency and end-to-end user waiting time need separate measurements. Source documents must be authorized, versioned, hash-matched and split into development/test sets. Each context must be a substring of its source. Duplicate normalized source documents are rejected, including duplicates assigned different IDs.

Use the generated dataset/config templates and the strict contracts in `evaluation/contracts.py`. Real datasets require `synthetic=false`, `authorized_material=true`, retrieval provenance `frozen_local_rag`, and accurate embedding metadata. The authorization field is an operator attestation, not a consent-management system. Up to fifty documents/cases, five unique seeds, three separate model pairs and one thousand total condition slots are accepted.

Tune on development only. Save its `protocol_sha256` and `development_source_hashes`; copy them into the test config as `frozen_protocol_sha256` and `development_source_hashes`, then set `split` to `test`. Test execution checks the unchanged prompts/code, model tags, seeds, budgets and policy, and rejects test source hashes in that ledger. Keep the development dataset and complete experiment record; near-duplicate documents, conceptual leakage and honest split designation still require human review. Any protocol change requires a new development freeze.

## Local models: hardware validation pending

**Hardware-validated model selection: pending.** No inference was performed for Phase 19. The user's 8 GB Windows laptop stays in mock mode. No paid API, cloud model or automatic download/fallback exists. Gemini names in the earlier diagrams are not locally executable Ollama checkpoints and are not used.

The operator-only command is available for a later authorized hardware trial:

```powershell
.\.venv\Scripts\python.exe -m evaluation run DATASET.json CONFIG.json --allow-local-inference
```

Set `mode` to `local` and specify each pair's `generator` and `verifier` tags in the experiment config. Production keeps its existing environment-variable model configuration; experiment configs deliberately record their own exact pair. The present adapter accepts only the existing tiny `qwen2.5:0.5b-instruct-q4_K_M` transport profile. It requires the model and tokenizer already installed, the existing memory floor, bounded context/output and CPU-only sequential execution. Different checkpoint support requires tokenizer/template validation and a separate hardware trial before extending this guard. A configurable field does not imply every model is supported.

Stop other AI work before running. The adapter checks no model is already loaded, verifies model digests before/after calls, budgets the local tokenizer without silent truncation and requests unload after each call. The evaluation lock does not coordinate unrelated Ollama clients. A failed unload or unrelated concurrent client can stop later calls. Hardware rejection remains an error, never a fallback. Same-checkpoint generator/verifier runs are labelled `same_checkpoint`; separate prompts do not establish independent model errors.

## Human review and reporting

Use [the rating rubric](../evaluation/RUBRIC.md). The pack contains one item per unique candidate, randomized blind IDs, full reference text and requested attributes. Model and condition labels are hidden; source citations/content can still reveal condition. Two raters review independently. Duplicate the blank rows with a distinct reviewer ID, collect both sets into one ratings array, and keep the exact `run_sha256`. A third distinct reviewer may adjudicate after two independent ratings. Disagreement or missing labels remain unresolved unless properly adjudicated. The verifier's own opinion is never a human quality label.

```powershell
.\.venv\Scripts\python.exe -m evaluation report evaluation/runs/RUN/run.json evaluation/runs/RUN/rated-summary.json --mapping evaluation/runs/RUN/review/OPERATOR-ONLY-map.json --ratings evaluation/runs/RUN/review/collected-ratings.json
```

Reports separate each model pair and condition. They include requested/generated/retained counts, generation failures, retention among generated candidates, end-to-end yield among requested slots, verifier decisions and mathematical outcomes. Quality is reported both before and after filtering with rated, eligible and unresolved denominators. Difficulty agreement compares independent difficulty labels to requested difficulty. Complexity is a rubric score, not accuracy. Exact normalized-stem repeats are a diagnostic; semantic diversity and duplicate detection accuracy remain to be evaluated. Human duplicate labels describe similarity across the blinded review pack, which mixes conditions; they must not be interpreted as within-condition diversity or as a penalty for expected A/B overlap.

False acceptance is PASS among independently labelled invalid candidates with a verifier decision. False rejection is REJECT among independently labelled valid candidates; a separate measure counts all valid candidates not passed, including REGENERATE. These denominators exclude unresolved labels and verifier execution errors, which are reported separately. Human ratings on mock runs never become AI research metrics.

Two-rater valid/invalid agreement and Cohen's kappa are available when defined; degenerate kappa remains null. Quality intervals resample source-document clusters (500 fixed-seed bootstrap replicates), are absent below two documents and remain exploratory for small samples. Repeated seeds/items from one source are not independent documents. These are per-condition intervals, not paired effect tests. Do not claim significance by comparing interval overlap. A formal comparison needs a prespecified paired analysis and adequate independent sources.

Successful local calls preserve Ollama's load/evaluation/total durations separately in raw generation metadata and verifier call metadata. Stage wall-clock summaries include failed calls and provide p50/p95; B generation timing is reused in C/D, so do not sum all condition records as actual run cost. No cold/warm performance conclusion follows from an unload request. Peak full-stack memory, paging, retrieval/queue latency, student satisfaction and learning outcomes remain **To be evaluated**. Review time is recorded only when raters supply it.

## Adaptive-policy replay is a separate study

Select up to eight owned classroom assessments and explicitly confirm permission and participant consent. Only released, submitted first-exposure evidence is exported. Skips, repeats, expired attempts and currently quarantined items are excluded. Mixed ownership is rejected as a whole. Exports over ten thousand eligible events are rejected rather than truncated.

Each export uses fresh pseudonyms, omits names/emails, raw IDs, comments, question text and event timestamps, and retains an ordering sequence. Pseudonymous records are not guaranteed anonymous: keep them private. Selection changes reset browser confirmation. The checkbox records an attestation; obtain actual permission separately. Cross-export identity linkage is intentionally unavailable.

```powershell
.\.venv\Scripts\python.exe -m evaluation replay private-adaptive-events.json adaptive-replay.json
```

Replay compares a fixed easy policy with the existing adaptive recommendation **before each recorded answer**, using only earlier exported evidence. Missing history affects decisions. It cannot assign observed answers to unasked questions, establish learning gain or compare causal policy effects. A later learner study needs prespecified consent, sampling, randomized/counterbalanced allocation, comparable pre/post measures, attrition handling and learner-cluster analysis. No such study or satisfaction survey has been run.
