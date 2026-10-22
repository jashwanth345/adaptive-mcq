# Analytics — Phase 18

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

13 October 2026. Operational analytics are implemented; research evaluation is still planned. All computation runs locally in PostgreSQL. No new dependencies, model execution or service charges.

## Access and navigation

Students: **My analytics**, with a link to the existing **My learning** recommendations. Teachers: **Classroom analytics** for all owned classroom assessments. Open **Assessments → select assessment → View assessment analytics** for one assessment, including assessments without attempts. History links can also select an assessment.

| Endpoint | Access |
|---|---|
| `GET /api/v1/student/analytics` | Current student's own classroom and private-practice attempts |
| `GET /api/v1/teacher/analytics` | Current teacher's owned classroom assessments |
| `GET /api/v1/teacher/assessments/{id}/analytics` | One owned classroom assessment; foreign/unknown IDs return 404 |

All accept `offset` (0–1,000,000) and `limit` (1–50, default 20) for **history only**. Aggregates cover the full selected scope. The assessment endpoint accepts `ranking=true`; default false. Teacher role, active account and ownership are enforced both at the API and inside the scoped SQL function. Student identity always comes from the authenticated principal. Responses are no-store.

## Metric contract

| Metric | Numerator / denominator or definition |
|---|---|
| Recorded attempts | Current snapshot-session attempts in scope; ongoing, submitted and expired counts are separate |
| Participating students | Distinct students with those attempts, not enrolled students or submissions |
| Average recorded score | Arithmetic mean of `100 × awarded points / possible snapshot points` across visible completed attempts; includes expired and repeat attempts |
| Answered-item accuracy | Correct selections / non-skipped selections on currently approved versions in visible completed attempts |
| Incorrect / skipped | Incorrect selections and null selections are separate; skips contribute zero to original scores but are excluded from accuracy's denominator |
| Excluded items | Completed item exposures on versions no longer approved, including quarantined versions; repeated exposures count separately |
| Topic / difficulty / type | Same accuracy definition, grouped by immutable version metadata; topics use IDs, so same-named topics in different banks do not merge |
| Average elapsed time | Mean of `max(0, min(submitted time, deadline if present) − start time)` for visible completed attempts; includes idle time, is not active study time |
| Most missed questions | Top 20 approved versions by `(incorrect + skipped) / completed exposures`, then exposure count; both exposures and distinct students are shown |
| Feedback | Report/rating rows attached to in-scope attempts; distinct issue reporters, unresolved issue reports and helpful/poor rating counts are separate |

Zero denominators return **null**, displayed as **No data**. Per-question response time is not currently recorded and no average is invented. Counts are exact database-derived counts at the query snapshot; display percentages are rounded to one decimal. Readiness/timeouts retain the existing database service limits. This is not a large-scale performance benchmark.

## Release, quarantine and timing

Students see completed scores/performance only after the assessment release policy permits it. All score-derived summaries, breakdowns, excluded-item counts and elapsed-time metrics respect that filter; withheld history has null values. Teachers can see owned classroom outcomes before release. Feedback counts can include withheld attempts because submitting feedback does not require solutions to be released.

Quarantine does not rewrite stored answers or awarded points. Recorded averages/history retain original scores and show excluded-item counts. Accuracy and performance breakdowns exclude unapproved versions. For grade disputes, use the existing feedback review workflow; this feature does not automatically regrade.

Overdue attempts still marked in progress are counted separately, with no inferred score. Analytics is read-only and does not finalize them. Opening/submitting the attempt invokes the existing timeout behavior. Historical records lacking `attempt_sessions` are excluded, with this limitation visible in the UI.

Repeated attempts and expired outcomes are useful operational records but are **not** additional independent mastery evidence. The linked learning profile continues to use its separate first-exposure, released, submitted, approved-answer rules and provisional policy.

## Optional ranking boundary

The owning teacher can enable a ranking while viewing one assessment. It uses each student's best submitted attempt with no excluded items; expired attempts are omitted. Ties use the unrounded score and standard competition ranks (1, 1, 3). Repeats choose the earliest equally scoring submission, then ID, deterministically. Display names are the same permitted identities the owning teacher can see in the assessment roster/history.

The toggle is local to the current page and defaults off when reopening. This is a **teacher-only classroom ranking**, not a published student leaderboard, public ranking or cross-course competition. Students never receive classmates' records through analytics. Any future student-visible leaderboard needs a separate consent/display policy.

## Feedback interpretation

Reports are assigned to the attempt on which they were first recorded. A repeated report on a reused version may have been deduplicated into a different assessment's original report; it therefore does not appear in this assessment's report count. Version-wide investigations remain available in Feedback review. Report counts are not factual accuracy, an error rate, satisfaction research or causal evidence of learning improvement.

## Local database upgrade

Use the existing trusted migration operator to apply migrations through **011**, then apply [analytics runtime grants](../database/analytics_runtime_grants.sql) after prior module grants. Runtime gets execute permission on the scoped read function only, with no additional table privileges. Historical migrations remain unchanged. Native PostgreSQL deployment/authentication/concurrency checks remain pending; automated workflows use disposable embedded PostgreSQL.

## Remaining boundaries

No model evaluation metrics, learning-gain estimates, cohort comparisons or fake sample charts. No per-question timing, automatic regrading, background expiry sweep, public leaderboard or arbitrary date filter. Research experiment/export harness is Phase 19. The current pages/API report activity and provenance-compatible identifiers; they do not claim to establish AI reliability.
