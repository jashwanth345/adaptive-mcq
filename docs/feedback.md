# Student feedback, quarantine and review — Phase 17

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

The feature runs on the existing **FREE / OPEN SOURCE** local stack. It adds no dependency, AI inference, paid API or cloud service. Reports are evidence for human review, not proof of a defect or model-training data automatically applied to a model.

## Student workflow

After a submitted or expired attempt, expand **Report or rate question N**. Choose a category, optionally add a comment of up to 2,000 characters and send. Reports refer to the exact immutable question version and legitimate attempt. Ongoing, unknown and another student's attempts are rejected. Reporting is also available while results await teacher release; the form exposes no additional key, explanation or teacher-review notes.

Categories: wrong answer, wrong explanation, ambiguous, poor wording, weak distractor, too easy, too difficult, duplicate, not from material, mathematical error and other. A separate rating category accepts helpful or poor. One rating and one report per issue category per student/version are retained across attempts. A retry with the same request key returns the original result; a new request for an already-reported category returns a duplicate notice and preserves the original comment/rating. This phase does not edit or retract submitted reports.

**My feedback** lists only that student's reports with status and a link to the original attempt. Reports include no other student identities or internal owner-decision notes. Comments are shown as text, not interpreted as HTML, prompts or instructions. Students are asked to avoid personal information.

## Owner review

**Feedback review** lists cases for owned question versions. Teachers see their classroom questions; students can review only their own private practice content. Owning private content does not grant access to a teacher's review queue. A teacher who loses that role cannot review classroom-linked versions through a remaining student role. Owner review shows comments without reporter names, emails or account IDs; this is restricted visibility, not a claim of formal anonymity.

Counts use distinct students:

- Exposures: students who received the exact version in an attempt snapshot, including ongoing and expired attempts.
- Issue reporters: students with an issue category or a poor rating. Multiple categories and repeat attempts do not inflate the numerator.
- Unresolved reporters: those with open/reviewing issues or poor ratings.
- Helpful/poor: distinct students who provided each rating.

The unresolved-reporter/exposure ratio is a triage indicator, not an error rate or accuracy measurement. Elevated priority defaults to at least **3** unresolved reporters and a ratio of at least **0.20**. Configure `FEEDBACK_MIN_REPORTERS` (1–100) and `FEEDBACK_REPORT_RATIO` (0–1) in the local backend environment. These thresholds are design assumptions **to be evaluated**. Counts never automatically confirm a defect or change a student's mastery. The queue orders pending score reviews first, then active cases, then most recently updated; priority badges inform owner judgement within that ordering.

An owner can mark a case reviewing, dismiss its unresolved reports with a note, or explicitly confirm a defect. Decisions require a nonblank 3–600 character note, current case revision and retry key. A new category report increments the revision and reopens a non-confirmed case; a stale decision must reload. Helpful-only cases are visible for review but do not count as unresolved issue reporters.

## Quarantine and correction

Confirming a defect atomically records the decision/audit, resolves current reports, quarantines the exact version and creates a pending score-review task. The UI requires explicit confirmation. The version cannot be reapproved in place, even after a fresh passing verification report. Database release gates enforce this rule independently of the UI. Review actions cannot erase a confirmed defect.

Quarantine prevents new classroom attempts/publication using the item and prevents private practice selection/start. Existing admitted attempts preserve their snapshots and may finish to their original deadline, as established in Phases 14–16. Results preserve the original score, mark the defective item under review and withhold its solution. Recomputed learning profiles exclude its evidence without deleting historical events.

The score-review task shows the count of completed affected attempts. An owner records a follow-up note and acknowledges review. **Acknowledgement does not change scores, regrade or restore the item.** If an already-admitted attempt completes later, the task reopens automatically with a new revision. Automated retroactive regrading and student notifications are not implemented in this phase.

Teachers use **Inspect source evidence or create a corrected version** to enter the existing Teacher review screen. Editing creates a new immutable version; it needs fresh verification, deterministic validation and teacher approval. Previously published assessments still refer to the old version and must not be silently rewritten; prepare a new assessment for the corrected version. Private students can inspect their own draft and generate a replacement through Draft studio. No automatic LLM job is launched by a report or decision. Changing prompt/rule versions requires a separately evaluated change; feedback does not retrain model weights.

## API and storage

All routes require a live authenticated session. The server supplies the account identity; body-supplied owner/student IDs are rejected.

| Method | Path after `/api/v1` | Purpose |
|---|---|---|
| POST | `/student/attempts/{id}/feedback` | Report/rate an exact version from a completed own attempt |
| GET | `/student/feedback` | Own report history |
| GET | `/feedback/reviews` | Owned case queue, counts and configured triage policy |
| GET | `/feedback/reviews/{version_id}` | Owned case, paginated reports and latest 20 decisions |
| POST | `/feedback/reviews/{version_id}/decisions` | Revision-checked review/confirmation/acknowledgement |

Lists accept offset/limit (default 20, maximum 50). Case details paginate reports; all decision history is retained even though the UI displays the latest 20. Student history never includes owner-decision notes. Existing no-store responses and body-size limits remain active.

[Migration 010](../database/migrations/010_feedback.sql) preserves legacy report rows, adds rating/other categories, creates cases for existing reported versions, and adds append-only request/decision records. Legacy repeat rows are not deleted; distinct-student aggregates avoid inflated counts and future submissions deduplicate against all existing rows. Runtime mutations use narrow functions with fixed schema paths and reporter/owner locking consistent with attempts and publication. A failure rolls back report/decision, quarantine, case revision and audit together.

After earlier module migrations/grants, the trusted local operator must apply migration 010 and [feedback runtime grants](../database/feedback_runtime_grants.sql). Do not grant direct feedback, case, decision or release writes to the app role. The new forward migration refreshes the teacher-approval guard to reject confirmed versions; existing migration files remain unchanged.

## Validation boundary

Positive tests use explicitly synthetic eligible questions in disposable PostgreSQL fixtures. They prove workflow behavior, not actual AI quality, report reliability, learning improvement or validated review thresholds. Mock-generated application drafts remain blocked from scored release. Native Windows PostgreSQL/pgvector deployment, native password authentication, multi-connection concurrency and real-model hardware/quality validation remain pending. No research slide or experiment result is updated from these tests.

Next: **Phase 18 — analytics**. Detailed assessment-impact listings, cross-topic analytics and evaluation dashboards remain in that phase; this review workflow supplies scoped counts and auditable decisions.
