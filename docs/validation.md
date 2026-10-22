# Deterministic validation — Phase 12

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

## Use the website

Open an owned saved draft in **Draft studio → Validation workspace → Run validation**. The saved report shows format/source checks, duplicate candidates, mathematical-check status and release blockers. Reopen it from the private, paginated validation history. A report is a snapshot: after creating/editing/archiving questions or adding a verifier report, run validation again. Release/publication independently check freshness.

Default test-generated questions remain **Release blocked**, even when individual deterministic checks pass. Test review is not real-AI evidence. A real-AI draft can become **Technical checks passed · not approved** only when all technical prerequisites pass. Every report still has `publication_eligible=false`. Classroom publication requires teacher approval; the separate student-practice path may use fully checked automatic release under the original blueprint. There is no approval, automatic-release or publication API in this phase.

Under **Try the arithmetic checker**, load the clearly labelled arithmetic example or enter your own expression/options/key. This is an **unsaved preview**, separate from the saved draft, and cannot grant release eligibility. Editing a field clears the previous preview result. The example tests deterministic calculation, not an LLM or educational effectiveness.

## Supported mathematical scope

The checker independently calculates exact rational values using Python's standard-library `ast` and `fractions.Fraction`. It never invokes `eval`, `exec`, a shell, SymPy parsing, an LLM or a network service. AST traversal accepts only numeric literals and specified operators.

| Supported | Examples / limits |
|---|---|
| Full question grammar | `Calculate: (3 + 5) / 2` or `Evaluate: 0.1 + 0.2` |
| Numeric options | Exactly four expressions, such as `4`, `1/2`, `0.25` |
| Operators | `+`, `-`, `*`, `/`, `**`, unary signs and parentheses |
| Powers | Integer exponent from −8 to 8; zero-to-zero is rejected as undefined |
| Bounds | 128 characters/expression, 24 characters/literal, 40 AST nodes, depth 12, 128-bit numerator/denominator |
| Precision | Exact fractions; no floating-point tolerance or implicit rounding |

A mathematical pass requires four numerically distinct options, exactly one option equal to the computed value and that option matching the proposed key. Therefore `0.5` and `1/2` are duplicate options even though their strings differ. Missing/wrong answers, equivalent distractors and division by zero fail. Variables, calls/imports, attribute access, collections, scientific notation, units, percentages, equations, square roots, symbolic algebra and rounded answers are outside this grammar. Unsupported expressions/resource limits never receive a pass. No user expression is executed as Python code.

Saved draft checks derive the expression from the immutable full stem; the caller cannot supply a separate “correct expression” unrelated to the question. Current generation remains conceptual only. A conservative numerical-keyword/digit/operator screen marks suspicious conceptual stems unsupported unless they match the exact grammar. A plain conceptual stem can be marked `not_applicable`; this screen is not a proof that prose contains no mathematical reasoning. Human review remains required. More general math needs dedicated specifications/validators in future work, not guessed extraction or a trusting LLM.

## Duplicate policy

Policy version: `deterministic-validation-v1`. Compare against the latest version of every other non-archived question owned by the same account. Older versions of the current question are excluded; separately, a superseded current version is blocked. Questions from other users never enter the comparison or response.

Normalization uses Unicode NFKC, case-folding, word tokens and selected mathematical operators. Exact normalized stems block readiness. A token-set Jaccard similarity of at least **0.85**, with at least four tokens on each side, flags similar wording and also blocks readiness. This is an initial engineering heuristic, not an experimentally tuned threshold or MCQ-quality score. It ignores word order and may overflag negation/rephrasing or miss semantic paraphrases. Human review/editing is needed to resolve candidates; Phase 12 offers no override.

At most **2,000 other questions** are scanned. An additional row is fetched to detect overflow; a larger corpus is incomplete and cannot pass. Return at most ten candidate IDs/kinds/similarities plus total match count, without another user's content. The report stores an MD5 fingerprint of the ordered latest-version IDs, computed in PostgreSQL. It is a freshness token, not a security/content hash. Immutable version content and version IDs supply the underlying identity. Source SHA-256 integrity checks remain separate.

## Release prerequisites

The report service runs with the shared RAG/generation gate and the owner's generation advisory lock; use one backend worker. It creates an immutable validation report and audit event atomically. Matching request retries return the original snapshot; use a fresh key to revalidate changed evidence. A retry key used for a different version is rejected.

Technical readiness requires:

1. An owned, current, non-archived version with actual `mode=ollama` generation provenance.
2. A latest actual-AI advisory `PASS`, `ai_executed=true`, and blind answer agreeing with the key.
3. Valid question schema and owned source quotation/excerpt/hash integrity.
4. A complete duplicate scan with no candidates.
5. A supported mathematical pass, or conceptual `not_applicable` after conservative triage.

These checks are software rules, not a factual-correctness guarantee. No model accuracy, confidence score or MCQ-quality percentage is manufactured. Same-checkpoint model calls do not establish independent-model verification. Hardware/quality trials remain pending.

Migration 005 adds a database check on approval and assessment publication. It requires the latest passing validation for that immutable version, unchanged comparison corpus and latest verifier report, an active owner, a current/non-archived question, and non-archived source material. An explicit reviewer must be the owning teacher. An automatic release with no reviewer is permitted only for a student owner and cannot satisfy classroom publication's teacher-approval requirement. Existing release-gate verification and source requirements still apply to both paths. Thus an old PASS cannot override a later failed report, a new question can invalidate the corpus snapshot, and a new edit cannot reuse its previous version's readiness. Quarantine remains possible when evidence is stale. A successful validation report is never itself an approval.

There is no teacher editing/approval UI or release-write permission in this phase. The existing historical `question_verifications` schema still has its earlier score fields; this service does not fill them with invented values. Future teacher-review work must define the bridge to release evidence explicitly.

For a retained database, the additive migration preserves existing records and historical scores; it does not silently rewrite old approvals. Attempts to approve/reapprove or newly publish without fresh required evidence fail. Existing already-published records are not retroactively regraded/quarantined by this migration. Review any retained legacy approvals before exposing them through future assessment workflows. The validation API permits an owner to revalidate a released generated version for freshness, but cannot edit or republish it.

## Local setup and APIs

All components used here are **FREE / OPEN SOURCE** and already installed: Python standard library, FastAPI, Pydantic, SQLAlchemy, PostgreSQL/pgvector, React, Vite and existing test tools. No runtime package, paid API, cloud service, model weight or subscription was added. Ollama is not started for these checks.

Use the existing native PostgreSQL/pgvector setup guide. As the trusted operator, apply the current migration plan (now 005) and then the additive grant file:

```powershell
.\.venv\Scripts\python.exe database/migrate.py plan
.\.venv\Scripts\python.exe database/migrate.py apply --psql 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --host 127.0.0.1 --port 5432 --database adaptive_mcq --user adaptive_mcq_migrator
psql -h 127.0.0.1 -U <database-owner> -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f database/validation_runtime_grants.sql
```

Preserve existing private configuration. Keep `GENERATOR_MODE=mock` and `VERIFIER_MODE=mock`; no new settings are needed. Start the local backend and frontend using the existing launch guides. Native PostgreSQL/pgvector deployment remains pending on this laptop; disposable tests do not install a retained application database.

| Authenticated endpoint | Contract |
|---|---|
| `POST /api/v1/validation/drafts/{version_id}/reports` | UUID `idempotency_key` only; owner-scoped snapshot |
| `GET /api/v1/validation/drafts/{version_id}/reports?offset=0&limit=3` | Private history, page size at most ten |
| `POST /api/v1/validation/math-check` | `stem`, exactly four bounded `options`, integer `correct_option` 0–3; unsaved preview |

Responses use no-store headers and JSON request bodies are capped at 16 KiB. Client fields cannot set mode, owner, verdict, computed answer or release eligibility. Database credentials remain server-side; API ownership enforcement and composite foreign keys do not imply per-user database row-level security. The runtime role has report SELECT/constrained INSERT and corpus-function access, without report UPDATE/DELETE or release writes.

See [Phase 12 completion evidence](phase-12-completion.md) for actual tests and limitations. Native multi-connection contention, large-corpus performance, semantic duplicate recall and broader math capability remain to be evaluated.
