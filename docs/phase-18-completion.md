# Phase 18 completion — analytics

**Phase 18 is complete within the local software scope, 13 October 2026.** This establishes operational analytics, not research or model-quality results.

## Delivered

- Student and teacher analytics, with a dedicated filter/link for each owned classroom assessment.
- Actual attempt/student counts, original average scores, answered-item accuracy, elapsed attempt time and explicit correct/incorrect/skipped/excluded counts.
- Topic, difficulty and question-type breakdowns with denominators; distinct topic IDs stay separate even when names match.
- Top 20 most-missed approved question versions with counts and direct teacher-review links.
- Feedback counts and ratings linked to the original reporting attempt, without claiming factual accuracy or student-study satisfaction.
- Paginated attempt history with scope-wide aggregates and student result-release enforcement before score-derived computation.
- Optional teacher-only ranking for a single classroom assessment; best submitted attempt per student, tied ranks, no excluded items, disabled by default.
- Original scores preserved after quarantine; affected items excluded from accuracy/breakdowns/ranking. Read-only analytics never finalizes overdue attempts.
- Sidebar and assessment-library navigation, responsive metric cards/tables, clear empty/error/loading states and links to existing provisional mastery recommendations.
- Forward migration 011, restricted function grants, API version 0.18.0 and [metric/API guide](analytics.md).

## Verification

| Check | Result |
|---|---|
| Focused analytics backend workflows | 5 passed |
| Full backend regression | 241 passed; one prepared local-embedding snapshot test intentionally skipped; existing Starlette/httpx deprecation warning |
| Frontend regression | 108 passed across 14 files |
| Production frontend build | Passed |
| Database checks | 113 passed: 55 schema/migration, 36 validation/publication, 8 attempt/adaptive, 8 feedback, 6 analytics |
| Migration-runner checks | 7 passed |
| Python lint | Passed |
| Local browser integration and visual review | 12 checks passed; desktop 1440 × 1000 and mobile 390 × 844 inspected; no page errors or external requests |

Automated data are synthetic and disposable. No real learner measurements, LLM accuracy, performance gains or model inference are implied. Initial test-helper errors were corrected; migration-runner temporary files use the workspace temporary directory to avoid sandbox temporary-folder access failures.

## Local setup and remaining boundaries

Apply migrations through 011 and [analytics runtime grants](../database/analytics_runtime_grants.sql) with the trusted local database operator. No existing native database, real account or local secrets were changed. Native PostgreSQL/pgvector deployment/authentication/concurrency and Hardware-validated model selection remain pending.

The core stays local and free; no dependency download, model download, inference or paid service was introduced. Per-question timing is not recorded. Analytics includes repeated/expired attempts as operational activity; mastery retains its distinct evidence rules. Teacher-only ranking does not publish peers' data to students. Research evaluation/exports remain Phase 19.


## Visual evidence

Screenshots contain **synthetic workflow data**, not real student/model results:

- [Student desktop](images/phase-18-analytics-student-desktop.png) and [student mobile](images/phase-18-analytics-student-mobile.png).
- [Teacher desktop](images/phase-18-analytics-teacher-desktop.png) and [teacher mobile](images/phase-18-analytics-teacher-mobile.png).

**18 of 24 phases complete; 6 remain. Next: Phase 19 — evaluation harness.**
