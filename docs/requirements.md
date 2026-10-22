# Phase 1 requirements baseline

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Baseline: 1.0, 5 October 2026. Status: requirements and architecture established for phased implementation. All functional rows below are **Planned**, not implemented. The user's explicit Phase 1 authorization establishes the planning scope; it does not establish experimental success.

## Objective and authority

Build an adaptive MCQ platform for teachers and students using local retrieval, separately configured generator/verifier roles, deterministic supported-math checks, teacher-controlled publication, student practice, feedback and evaluation. The latest user instructions take precedence over the older Gemini/cloud diagrams. Core service-fee target is ₹0 on existing hardware. No payment, credit card, hosted database, cloud model or paid fallback may be required.

The original IEEE paper is a research source, not a list of implementation accomplishments. Its adaptation, feedback and teacher involvement are acknowledged. The missing 2025 citation remains an evidence gap. No accuracy, latency, learning gain or completed software is inferred from diagrams or sample UI figures.

## Users and access

Teachers own courses, materials, question banks and published assessments. Students own private uploads/practice and their attempts. Teachers can see only authorized course/assessment participants. Public role selection cannot grant access to another teacher's data. Teacher enrollment is controlled during the local demonstration. Every object access and vector retrieval must enforce ownership/membership at the backend.

## Functional acceptance checklist

| ID | Requirement | Acceptance scenario for its implementation phase | Primary phases |
|---|---|---|---|
| R01 | Login, logout, roles and separate dashboards | A student cannot call teacher-only publication or inspect another student's private material | 4–7, 21 |
| R02 | Course, subject, topic and optional chapter | Teacher can create topic metadata and only access their authorized course scope | 2, 6 |
| R03 | PDF and pasted-text material input | Valid text PDF yields page-linked chunks; unsupported/scanned input returns an explicit status | 8 |
| R04 | Topic-only generation | Uses an authorized existing corpus; missing material asks for input instead of inventing citations | 9–10 |
| R05 | Generation configuration | Count, five difficulty labels, question type, cognitive objective and English language are stored with the job | 10 |
| R06 | Local RAG | Chunk/source IDs, document version, embedding revision and retrieved context can be inspected for each generated item | 8–10 |
| R07 | Generator contract | Emits stem, four distinct options, one key, explanation, topic/chapter, difficulty, cognitive level and provenance | 10, 12 |
| R08 | Separate verifier role | Blind solve receives no generator key/explanation; comparison pass records disagreement, reasons and evidence | 11 |
| R09 | Structured verification | Returns PASS/REGENERATE/REJECT plus specified criterion scores, issues and suggested fix; unresolved review is not PASS | 11–12 |
| R10 | Deterministic supported-math validation | Missing correct answer, equivalent duplicate options, invalid domain or ambiguous rounding prevents automatic release | 12 |
| R11 | Duplicate and diversity controls | Exact duplicates fail; semantic candidates follow calibrated checks; generated set reports type/cognitive coverage | 12, 19 |
| R12 | Teacher review actions | Approve, reject, edit stem/options/key/explanation/difficulty, regenerate item/set and preview are available; edit clears old approval | 13 |
| R13 | Safe deletion and reuse | Unreferenced draft may be deleted; published/referenced versions are archived and remain auditable | 13 |
| R14 | Question-bank filters | Filter subject/topic/difficulty/cognitive level/type/status/source/date/quality and reuse approved versions | 13 |
| R15 | Immutable publication | Publication transaction includes only eligible approved versions, and later edits do not alter active attempts | 13–14 |
| R16 | Reference codes | Authenticated join enforces published/active/allowed/expiry/attempt rules; code revocation blocks new access as specified | 14 |
| R17 | Assessment controls | Teacher sets count, expiry, attempt limit, time limit and question/option randomization; server enforces them | 14–15 |
| R18 | Attempt experience | Progress, navigation, flagging, save/resume and submission refer to stable question/option IDs and stored permutations | 15 |
| R19 | Correct scoring and release | Repeated submit creates one score; key/explanation/source solution is withheld until the teacher's release policy permits | 15 |
| R20 | Self-generation and practice | Student creates private practice without a reference code and gets validated questions with appropriate explanations | 7, 10–12, 15 |
| R21 | Adaptive topic profiles | Eligible valid first responses update evidence once; insufficient evidence is visible; difficulty moves by at most one level | 16 |
| R22 | Student analytics | Accuracy, time, counts, topic/difficulty/type performance, history and recommendations trace to actual answer events | 16, 18 |
| R23 | Feedback | Helpful/poor ratings, all issue categories and optional comments attach to the exact version and legitimate attempt | 17 |
| R24 | Feedback review | Distinct reporters/exposure and teacher decisions determine review; confirmed defects quarantine items and support correction | 17 |
| R25 | Teacher analytics | Counts, average score, missed/difficult items, topic/difficulty performance, reports and quality metrics derive from owned assessments | 18 |
| R26 | Optional classroom leaderboard | Teacher-controlled and assessment-scoped, uses permitted display names; no public cross-course ranking | 18 |
| R27 | Local model configurability | Generator/verifier environment values can change without code edits; missing local model gives an actionable error | 10–11 |
| R28 | Evaluation harness | Matched baseline/RAG/verifier/math ablations, configurable model pairs and separate adaptive study export provenance and denominators | 19 |
| R29 | Logs and recovery | Job status, retries, model/prompt metadata, timings and errors survive restart without exposing secrets/private documents | 3, 10–12, 20 |
| R30 | Fully local demonstration | Prepared application operates with internet disconnected and cloud disabled; no provider fallback is attempted | 20, 22 |

Grammar, ambiguity, factual correctness, answer/explanation correctness, distractor quality, relevance, source grounding, difficulty suitability and zero/multiple-correct detection are all verifier/quality-review criteria. Similarity and mathematics also have deterministic checks outside the LLM.

Question-type metadata accommodates conceptual, definition, application, scenario, numerical, code reading, debugging, output prediction, assertion/reasoning, case-based and higher-order questions. Initial functional release prioritizes source-based conceptual/application questions and supported numerical templates. The other single-correct types remain planned extensions, with type-specific evaluation before activation. Multiple-correct items require a separate option/key/scoring contract and are future work. This staging does not claim all requested types already work.

Bloom metadata separates Remember/Understand/Apply/Analyze/Evaluate from difficulty. Create remains a stored future objective, not a claim that a four-option question directly measures original creation. English is the initial supported language. Telugu/Hindi require corpus/model/language-specific review before availability.

## Quality and resource constraints

| ID | Requirement | Observable acceptance |
|---|---|---|
| N01 | No paid or hosted core dependency | Dependency/config review plus prepared offline end-to-end demonstration |
| N02 | 8 GB hardware awareness | One local inference job and one loaded LLM at a time, bounded context and measured peak full-stack memory |
| N03 | Fail closed on invalid items | Failed or unresolved gates never reach automatic student delivery |
| N04 | Accessible responsive UI | Keyboard operation, labelled controls, readable contrast, narrow/desktop layouts and useful error/empty states |
| N05 | Data consistency | Idempotent submission/update, pinned versions, constraints, transactions and crash-recovery tests |
| N06 | Security | Ownership/RBAC, upload constraints, parameterized queries, token validation, rate limits and no answer leakage |
| N07 | Reproducibility | Source hashes, model digests, prompts, configuration, seeds/repetitions and versions retained in evaluation records |
| N08 | Honest performance reporting | Separate queue/load/inference latency, retention yield and failure counts; no fabricated results |
| N09 | Local maintainability | Modular code and few services, actionable startup diagnostics, backup/restore procedure |

## Release boundaries

Classroom publication always needs teacher approval of the current question version. Private practice may use automated release only after all applicable checks pass, with a visible “automatically checked” label and report action. A report is a review signal, not automatic proof of a wrong answer. Confirmed defective items are excluded from subsequent selection and profile recomputation where appropriate.

Fixed graded assessments remain fixed. Adaptive selection is for practice unless a teacher deliberately enables a separately designed adaptive mode. No automatic model retraining occurs. No generated code execution, external browsing by the model, image-only PDF support or universal mathematical proof checking is included in the initial core.

## Unresolved empirical decisions

Model pairing/digests, memory/latency limits observed on this laptop, duplicate/quality thresholds, calibrated difficulty, adaptive decay/weights/windows/thresholds and learner-study sample size remain To be evaluated. These are explicit pending decisions, not hidden working defaults. Bounded retries and conservative context/output budgets are operational starting settings, not scientific results.
