# Student dashboard — Phase 7

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Students can now view their own stored activity, active course memberships and read-only attempt history, and save a starting-difficulty preference for future personal practice. Joining assessments, taking questions, feedback submission, released scores, AI generation and adaptive mastery remain planned.

## Local setup

Complete the [backend](backend.md), [authentication](authentication.md) and [frontend](frontend.md) setup. Existing student registration creates the required student profile. No production test account or password is supplied.

After authentication grants, apply the student permission script using the trusted database/schema-owner login. From the project root, for the default database and application role:

```powershell
psql -h 127.0.0.1 -U postgres -d adaptive_mcq -v ON_ERROR_STOP=1 -v runtime_role=adaptive_mcq_app -f database/student_runtime_grants.sql
```

Replace `postgres` with your actual database-owner login if different. Keep the existing teacher grants for teacher functionality. The new script grants selected read columns on student profiles, memberships, courses, materials, attempts, assessments and feedback, and UPDATE only on `student_profiles.preferred_difficulty`. It grants no answer/key access, enrollment creation, attempt writes or mastery writes. It does not create users or elevate the application role. All application users share a runtime database role; backend identity filters enforce student ownership.

No migration is required. Migrations 001–003 and their checksums remain unchanged. Foundation readiness checks authentication prerequisites; missing student permissions can still cause a safe 503 on dashboard requests. A missing student profile also returns 503 with an account-repair message, rather than silently creating or inventing data. The local operator must investigate missing profiles.

Start the backend and frontend as in the existing guides, open `http://localhost:5173`, and sign in as a student. Accounts with both roles can switch workspaces. Teacher-only accounts cannot call student routes.

## Student workflow and data meanings

| Section | Actual behavior |
|---|---|
| Enrolled courses count | Number of active course memberships for the signed-in student |
| Your study materials | Owned non-archived material records; excludes teacher/other student materials |
| Submitted attempts | Attempts whose student ID matches the session and whose state is submitted; includes classroom and practice |
| Your feedback | Number of feedback records submitted by that student, across all review states |
| Your courses | Latest six active enrollments, ordered by joined time then course ID; total shown when more exist |
| Practice preference | Saves Easy/Medium/Hard to the student's own profile; Easy is the existing registration default |
| Attempt history | Own recorded attempts, six per page, ordered by start time then attempt ID |

These are inventory/activity counts, not evaluation results or inferred performance. Empty records produce real zeros and empty states. Loading/failure displays unavailable values rather than substituting zero. No percentages, accuracy, streaks or mastery values are generated. Course lists reflect stored memberships; there is no enrollment or join-code action yet.

Select a starting difficulty with the mouse or keyboard and choose **Save preference**. Unsaved changes remain visible; failures keep the selected value available for retry. A successful response updates the saved state. Refreshing/reopening the dashboard loads the value from PostgreSQL. Dashboard refresh or history pagination discards unsaved form choices; save first. Concurrent sessions use the last successfully committed preference. This is not an adaptive algorithm, and it does not alter teacher-controlled assessments. Refreshing the browser still requires signing in again under the memory-only session policy.

Attempt history shows title, classroom/personal type, attempt number, start date and state. Historical metadata remains visible for the student's own attempts even if an enrollment later becomes inactive. The API includes an optional submission timestamp. It returns no student IDs, assessment IDs, answer keys, explanations, answer selections or scores. In-progress rows are records only; there is no resume button until the attempt workflow is implemented. Score/answer release will need its separate policy in that phase.

## API contracts

All endpoints require an active bearer session and the current server-side student role. The student ID always comes from that identity. Responses are `Cache-Control: no-store`.

| Method and path | Contract |
|---|---|
| GET `/api/v1/student/dashboard` | `preferences`, four stored counts and latest six active course memberships |
| GET `/api/v1/student/attempts?offset=0&limit=6` | `items`, `total`, `offset`, `limit`; limit 1–24 and offset 0–100000 |
| POST `/api/v1/student/preferences` | `{ "preferred_difficulty": "medium" }`; returns the stored preference |

Difficulty accepts exactly `easy`, `medium` or `hard`. Extra body fields, invalid values and invalid pagination return 422. Request bodies are capped at 16 KiB. Unauthenticated/invalid sessions receive 401; a teacher-only identity receives 403. Missing student profile or unavailable storage returns 503. Preference writes and an audit event commit together. No automatic write retry occurs.

Dashboard counts/courses/profile are read in a single SQL statement, and history total/items in another. Each response has its own consistent database snapshot; the two responses may represent slightly different instants. Backend filters use `attempts.student_id`, not the assessment owner's ID, because classroom attempts belong to students while their assessment belongs to the teacher.

## Source and validation

- `backend/app/student/`: schemas, protected routes, metadata queries and preference writes.
- `database/student_runtime_grants.sql`: operator-applied column permissions.
- `frontend/src/student/`: dashboard, preference form, history table and responsive styles.
- `backend/tests/test_student.py`: validation, isolation, pagination, profile/role errors and privileges.
- `backend/tests/test_student_records.py`: positive submitted-attempt/feedback counts using valid synthetic records, with result privacy assertions.
- `frontend/tests/student.test.tsx`: empty/populated rendering, preferences, failed writes, unavailable data/retry, pagination and session expiry.
- `frontend/tests/e2e.mjs`: actual backend preference save, keyboard control, refresh and fresh-login persistence, plus existing student/authentication/teacher checks.

Use the existing [frontend test commands](frontend.md) and backend integration test commands from [authentication](authentication.md). No dependency was added; the pinned stack remains **FREE / OPEN SOURCE**, local and without paid fallbacks. Test accounts and academic content are disposable fixtures, never application seeds or research results. See the [completion record](phase-7-completion.md) for observed results and remaining deployment limits.

## Phase 14 navigation update

Teacher accounts now have an **Assessments** page for drafts, publication, participant permissions and reference-code controls. Student accounts have **Join assessment** for authorized code entry and metadata previews. Existing dashboards continue to display stored counts/history. Attempts and scoring are Phase 15. See the [assessment guide](assessments.md).


## Phases 15 and 16 update

Attempt history now links to the player for managed attempts and released results. Starting difficulty is used by profile replay for private-practice recommendations. My learning exposes evidence coverage and an explicitly provisional index; no percentage is invented for an empty profile. Older imported attempts without managed sessions remain metadata only. See [attempts and adaptive learning](attempts-and-adaptive.md).


## Phase 17 update

Use My feedback for saved reports and Feedback review for your own private questions. Classroom reports are reviewed by the owning teacher. Reports never directly alter your score or learner profile; confirmed quarantine excludes the version from adaptive evidence. See [feedback](feedback.md).
