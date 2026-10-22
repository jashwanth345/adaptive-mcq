# Assessment attempts and adaptive learning — Phases 15 and 16

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

The new student attempt player saves choices and review flags, resumes stored progress, enforces server deadlines and submits for server-side scoring. My learning derives topic profiles and recommends an eligible unseen private question. All runtime components remain **FREE / OPEN SOURCE** on the existing local stack; no new dependency, paid service, inference or model download is needed for website development/tests.

## Classroom workflow

1. Join with the teacher's reference code. Select **Start or resume assessment** when ready. A timed attempt begins immediately; joining alone does not start the clock.
2. The server rechecks admission and current question eligibility. It creates one active attempt with immutable question-version IDs, item order, option permutations, points and deadline. Repeated starts resume the active attempt rather than consuming parallel attempts. A completed attempt consumes its allowance; an expired attempt does too.
3. Navigate questions, choose or clear an option, and flag items. **Save progress** commits choices/flags. Unsaved changes are labelled and prevent submission. Leaving via a link or reloading warns about unsaved changes. Progress is kept in the database, not browser storage. After signing in again, use the student dashboard's attempt-history link to resume.
4. Submit after saving, then confirm. Skips receive zero points. The server maps displayed positions through stored option permutations and grades against the immutable answer key. Clients cannot supply correctness, points or an answer key. A revision prevents one tab from silently replacing newer saved work; reload after a conflict. Request keys make retries safe.
5. For `after_submit`, finished results are visible immediately. For `after_close`, scores, correctness, solutions, source excerpts and associated learning evidence stay hidden until the teacher closes the assessment. Excerpts are limited to the item's stored evidence; no teacher file-download access is granted.

Code expiry/replacement/revocation, participant removal and assessment closure block **new starts**. An already admitted attempt retains its snapshot and may save/submit until its original deadline. This preserves the Phase 14 access boundary. Active account/role authentication is still required for every request.

Deadlines use the database clock. The browser countdown is only a display. At or after the deadline, the next view/save/submit finalizes previously saved answers as **expired** and ignores late changes. There is no background timer daemon: a dormant attempt transitions when next accessed. Expired attempts get an original-key score under the same release policy, but no learner evidence. No negative marking or partial credit is implemented. Per-question response timing is not inferred from the browser; stored start/submission timestamps support later diagnostics.

If a question is quarantined after presentation, its original attempt/score is preserved, its solution is withheld and the result is labelled under review. Its evidence is excluded from profiles. Phase 17 supplies correction and score-review acknowledgement; automatic regrading remains future work; historical scores are not silently rewritten.

## Private practice

My learning offers an unseen question from the signed-in student's own source-based question set. Eligibility requires a latest, non-archived version with current passing **real** verifier and deterministic validation evidence. Mock ancestry, missing evidence, rejection, quarantine or stale comparison corpus blocks practice. The server repeats those checks at start.

A categorical automatic-release record references the actual validation report; it does not invent the legacy numeric quality-score fields. Classroom publication still requires teacher approval. The automatic release cannot be used as classroom teacher approval. Private practice has one question per session, immediate released results, and no classroom code. After submission, return to My learning for the next recommendation. Existing private drafts can be prepared and checked in Draft studio. Without eligible real evidence, the page honestly shows no ready item; there is no scored mock substitute or cloud fallback.

## Adaptive policy

`bounded-performance-v1` is an implemented **candidate policy**, not a calibrated learner model. These are declared design assumptions, **to be evaluated**:

| Parameter | Value |
|---|---|
| Symmetric prior | 1 correct, 1 incorrect |
| Decay per later eligible topic response | 0.95 |
| Minimum observations per covered difficulty | 3 |
| Recent responses at the current level | 3 |
| Promotion threshold | 0.75 plus all three recent responses correct |
| Demotion threshold | 0.40 plus at least two of three recent responses incorrect |
| Easy / medium / hard index weights | 1 / 2 / 3 |
| Profile replay window | Latest 5,000 eligible responses per student |
| Recommendation pool | Up to 50 eligible unseen private versions |

For each topic/difficulty, compute `(1 + decayed correct sum) / (2 + decayed response sum)`. Only difficulty levels with at least three observations contribute to the weighted topic index. With no covered level, display **Insufficient evidence**, never an assumed zero or fifty percent. Show observations and covered levels beside the index. The weighted index is not comparable across differently covered topics/students without calibration.

Replay starts at the student's saved starting-difficulty preference (default easy). A student changing that explicit preference changes the replay's starting point. Each eligible response at the current difficulty can move the recommendation by at most one level; observations at another level do not trigger an immediate jump. Replaying the same retained events yields the same profile. The implementation uses a linear pass with three running difficulty accumulators to remain lightweight. Response time and student complaints do not directly penalize ability.

Evidence is recorded transactionally with submission, once per student and exact question version, on first exposure only. Skips, expired attempts, prior exposure in an earlier attempt, quarantined versions and unreleased results do not contribute. A skipped first exposure is not later converted into independent evidence by retrying the same item. Later quarantine excludes retained evidence during recomputation without deleting audit history. Feedback triage will use quarantine for confirmed defects; this phase does not interpret an unreviewed complaint as a defect.

Profiles are derived on request from retained `mastery_evidence`, authoritative answers and release state. The earlier `topic_mastery` table remains reserved for a future cache; no competing client-supplied percentage is written there. Topics retain their owner/course identity; equal names in separate users' banks are not automatically merged. Cross-bank topic alignment and psychometric calibration remain future work.

Selection prioritizes under-covered topics, then weaker sufficiently observed topics, then the nearest available difficulty, with a stable ID tie-break. It considers only unseen eligible versions from the student's own bank. If the recommended difficulty is absent, the nearest eligible level is explicitly identified; an empty bank produces no recommendation. Existing generation supports a narrow conceptual question set, so broad cognitive/question-type diversity is not claimed. Fixed classroom tests are never altered by this policy.

## API and storage

All paths begin `/api/v1/student`; every route requires a live student identity and no-store responses.

| Method | Path | Purpose |
|---|---|---|
| POST | `/assessments/{id}/attempts` | Start/resume admitted classroom assessment |
| GET | `/attempts/{id}` | Own snapshot/progress/result; lazy expiry finalization |
| POST | `/attempts/{id}/save` | Save displayed choices/flags with expected revision |
| POST | `/attempts/{id}/submit` | Finalize once using server keys |
| POST | `/practice/start` | Start an eligible owned private version |
| GET | `/learning` | Derived topic profiles, explicit policy and next recommendation |

Mutations require UUID idempotency keys. Save/submit require the latest revision. Saves accept distinct positions 1–50, selected display option 0–3 or null, and a boolean review flag. Unknown fields and client scores are rejected. The existing 16 KiB body limit remains. Keys and solutions are omitted from ongoing/embargoed responses, not merely hidden in the UI.

[Migration 008](../database/migrations/008_attempts.sql) adds automatic evidence, flags, session revisions/deadlines, command history and narrowly scoped attempt functions. [Migration 009](../database/migrations/009_adaptive.sql) supplies scoped retained evidence and private candidates. Apply all migrations with the trusted local operator, then [attempt grants](../database/attempt_runtime_grants.sql) and [adaptive grants](../database/adaptive_runtime_grants.sql) after previous module grants. The runtime role receives no direct answer, score, attempt, permutation, profile or mastery-evidence writes. Definer functions use fixed schema paths and consistent student/owner locks; unexpected failures roll back grading, events and command records together.

Existing historical rows and original score records are preserved. Pre-Phase-15 attempts without a managed session remain visible as history metadata but cannot be played through the new endpoint. Native Windows PostgreSQL setup, real database-password authentication and concurrent multi-connection behavior still need separate verification. Embedded PostgreSQL tests cannot establish those properties.

No measured model quality, latency improvement or learning benefit follows from the synthetic tests or provisional profile display. Hardware-validated model selection remains pending. The research slides are unchanged. Next is **Phase 17 — student feedback, quarantine and review**.


## Phase 17 update

Phase 17 now supplies completed-attempt reporting, owner triage and confirmed-defect quarantine. Quarantined versions remain excluded from derived profiles. Score-review acknowledgement records follow-up without retroactive score changes; late completions reopen review. See [feedback, correction and review](feedback.md).
