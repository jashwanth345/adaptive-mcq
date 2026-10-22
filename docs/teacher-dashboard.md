# Teacher dashboard — Phase 6

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

The Phase 6 teacher workspace reads the signed-in teacher's stored records and supports course creation and topic organization. Later phases add the PDF library, Draft studio, advisory/deterministic checks and [teacher versioned review/approval](teacher-review.md). No illustrative scores or fabricated activity are displayed. Assessment publication, reference codes and analytics remain planned.

## Local setup

Complete the existing [backend](backend.md), [authentication](authentication.md) and [frontend](frontend.md) setup. Apply the Phase 6 permission script with the database/schema-owner login, not the restricted application login. From the project root, for the default database and runtime role:

```powershell
psql -h 127.0.0.1 -U postgres -d adaptive_mcq -v ON_ERROR_STOP=1 -v runtime_role=adaptive_mcq_app -f database/teacher_runtime_grants.sql
```

Replace `postgres` with your actual trusted database-owner login if different. The script grants SELECT on courses, topics, materials, questions and assessments, plus column-limited INSERT on courses/topics. It does not create a database/login, grant UPDATE/DELETE or grant publication permissions. Apply the earlier authentication grants first. This is an explicit operator setup step; the application does not elevate itself.

No new migration is required; migrations 001–003 retain their contents/checksums. The existing foundation readiness endpoint checks authentication prerequisites. A missing teacher grant will cause teacher requests to return a safe 503 even if authentication readiness passes. The page shows unavailable counts with a retry action, rather than zero.

Create or enroll a teacher using the [operator CLI](authentication.md). Start the backend and frontend as documented, then open `http://localhost:5173` and sign in. There is no supplied production teacher account/password.

## Teacher workflow

1. Open **Teacher workspace**. Dual-role accounts can still switch to the student workspace.
2. Choose **Create course**, enter a subject/class title and save.
3. In the opened course panel, enter a topic and choose **Add topic**.
4. Open any existing course to see its topics. Course pages show six records at a time.
5. Use **Refresh overview** to retrieve the latest stored counts and lists.

Titles are trimmed, nonblank and limited to 200 characters. Control characters are rejected. Course titles are unique ignoring case within a teacher's workspace; topic names are unique ignoring case within their course. Separate teachers can use the same titles. Topic creation is limited to 100 per course for this phase. If a database already contains more than 100 topics, detail shows its total and first 100, and further creation is blocked.

Creation records are persistent and audited. A repeated identical create request returns a duplicate conflict rather than creating another row. An owner-specific PostgreSQL advisory lock serializes writes through these endpoints, including retries. This is application-path duplicate protection, not a new database uniqueness constraint; privileged direct SQL or future write paths must respect the same contract. Rename, delete, archive and enrollment management are not implemented in this phase.

## What the overview means

| Display | Stored-data definition |
|---|---|
| Your courses | Courses owned by the current teacher |
| Study materials | Owned, non-archived material records |
| Question bank | Owned, non-archived question records, across all review states; not an approved-question count |
| Classroom assessments | Owned classroom assessments in draft/published/closed states; private practice excluded |
| Recent assessments | Latest five owned classroom records, with course title and state; read-only |

Each summary response uses one SQL statement so its counts/recent records share a snapshot. Course list totals and page items likewise share a snapshot. The two separate dashboard requests need not describe the exact same instant. Timestamps break ties using IDs for deterministic ordering. No student answers, keys, credentials or other teachers' records are returned. Future performance analytics are not inferred from these inventory counts.

## API contracts

All routes require a valid active bearer session and the server-side teacher role. Ownership always comes from authenticated identity, never a submitted owner ID. Successful and error responses are `Cache-Control: no-store`.

| Method and route | Behavior |
|---|---|
| GET `/api/v1/teacher/dashboard` | Owned counts and latest five classroom assessment summaries |
| GET `/api/v1/teacher/courses?offset=0&limit=6` | Owned course page; limit 1–24, offset 0–100000 |
| POST `/api/v1/teacher/courses` | `{ "title": "Database Management Systems" }`; returns created course, 201 |
| GET `/api/v1/teacher/courses/{uuid}` | Owned course and its first 100 topics, with total topic count |
| POST `/api/v1/teacher/courses/{uuid}/topics` | `{ "title": "Relational algebra" }`; returns created topic, 201 |

The topic input uses `title`, while its response uses the database field `name`. Unknown input fields are rejected. Request bodies are bounded at 16 KiB. Cross-owner and nonexistent courses both return 404; malformed UUIDs/pagination/fields return 422. Duplicate titles or the topic limit return 409 with specific safe codes. Students receive 403. Invalid/revoked sessions receive 401; an identity with no roles is also rejected by existing authentication. Native database grants alone do not distinguish application users: service ownership filters provide this boundary.

The frontend's protected request helper sends the token from memory, clears rejected sessions, rechecks roles after 403 and ignores responses from a replaced session. Pending reads are aborted on navigation. Writes are not automatically retried; a network error may require inspecting/reloading the list before trying again. Duplicate protection makes an identical retry safe from an extra course/topic row.

## Files and validation

- `backend/app/teacher/`: response/input models, authorization routes and query/write service.
- `database/teacher_runtime_grants.sql`: narrowly scoped operator-applied permissions.
- `frontend/src/teacher/`: responsive dashboard, course/topic forms and styles.
- `backend/tests/test_teacher.py`: validation and disposable PostgreSQL integration checks.
- `frontend/tests/teacher.test.tsx`: loading, errors/retry, creation, duplicates, pagination, rejected sessions and role changes.
- `frontend/tests/e2e.mjs`: existing real-browser suite extended with teacher registration-by-fixture, dashboard/course/topic persistence and mobile checks.

No dependency was added: the existing stack remains **FREE / OPEN SOURCE**. Test fixture teacher credentials exist only in the disposable test harness; they are not seeded by the application launcher. See the [completion record](phase-6-completion.md) for actual test counts, visual verification and native setup limitations.

## Phase 14 navigation update

Teacher accounts now have an **Assessments** page for drafts, publication, participant permissions and reference-code controls. Student accounts have **Join assessment** for authorized code entry and metadata previews. Existing dashboards continue to display stored counts/history. Attempts and scoring are Phase 15. See the [assessment guide](assessments.md).
