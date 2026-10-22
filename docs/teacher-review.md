# Teacher review — Phase 13

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Implemented workflow: sign in as a teacher → **Teacher review** → select a latest owned question → inspect options, explanation and original PDF quotation → edit a new version or record a decision. Draft studio also links directly to a teacher's question. Students cannot access this workspace or its APIs.

## Edit, check and decide

- **Edit as a new version:** change the conceptual question, four distinct options, answer key, explanation, difficulty or cognitive level. Add a reason. The original version, reports and decisions remain unchanged. Topic, question type and original source quote are retained; changing the source requires a new generated question.
- Each edit retains the original generation run as **ancestry**, not a claim that the LLM authored the edited text. A separate immutable teacher event records the edit and note. Mock ancestry remains mock. Editing does not upgrade a fixture into real AI content.
- The new version starts without AI review, deterministic validation or approval. Any release of the preceding version is quarantined atomically. Saved assessment/attempt content remains pinned to its original version; quarantine prevents new use through existing gates.
- Run fresh advisory review and validation on the new version. **Refresh approval checks** after those operations. Default mock mode remains available for demonstrations but cannot enable approval.
- **Approve this version:** requires a note and explicit on-screen confirmation. The server rechecks ownership, current version, active teacher identity, current real AI evidence, passing validation, nonarchived sources and unchanged duplicate corpus. A stale screen cannot bypass these checks.
- **Reject this version:** records the reason and quarantines any release. That version cannot subsequently be approved; save a corrected version first. Older versions are read-only in this workspace.
- Approval saves a release decision; it does **not** create or publish an assessment. After corpus/evidence changes, refresh deterministic validation and renew approval. Future publication also rechecks eligibility.

## Evidence model

Migration `006_teacher_review.sql` adds `teacher_review_events`, including authenticated owner, base/result version IDs, action, request key, exact edit/note payload and validation-report pointer for approvals. Events cannot be updated or deleted.

`question_releases` now supports exactly one evidence path:

| Path | Stored evidence |
|---|---|
| Historical / legacy | Existing `verification_id` and its original schema rules |
| Teacher categorical approval | `teacher_review_id` → immutable teacher event → exact validation report → exact advisory verifier report |

The new path **does not manufacture the seven numerical score fields** in the legacy verification table. Categorical model judgments are not experimental scores or guarantees of correctness. The existing automatic private student-practice release contract remains distinct; this phase does not expose an automatic-release API.

Database gates reject mock content, stale versions/reports/corpus, teacher-rejected versions and mismatched evidence. Source links become sealed once any advisory or deterministic review exists. New publication requires the teacher approval to reference the latest validation report. Historical already-published data is not rewritten.

## API and transaction contract

All routes below are under `/api/v1/teacher/reviews`, authenticated with a current teacher role. Owner identity comes from the session; payloads cannot supply owner IDs, AI mode, verdicts, scores or release state.

| Method / suffix | Purpose |
|---|---|
| GET root `?offset=0&limit=6` | Latest owned nonarchived questions, including decision status; maximum page 24 |
| GET `/{version_id}` | Exact question/source, current-version flag, decision state and approval readiness |
| GET `/{version_id}/versions?offset=0&limit=5` | Immutable version/decision history; maximum page 10 |
| POST `/{version_id}/edits` | Strict bounded fields, required note and UUID `idempotency_key` |
| POST `/{version_id}/decisions` | `action: approve | reject`, required note and UUID `idempotency_key` |

Expected failures return safe structured messages: unavailable question (404), role/identity failure (403 or authentication 401), stale version/conflicting retry/rejected version/blocked approval (409), invalid fields (422). Requests retain the existing 16 KiB cap and no-store response policy.

`teacher_review_action` executes content/options/source copy, event, release change and audit atomically. It takes the same owner advisory lock as generation and validation, then locks the base version and checks it is current. Retries with the same key and payload return the original result; changed payloads conflict. A retry after a later edit returns the original saved version with its current superseded status, not a new edit. Unexpected database failures roll back the transaction. Expected business refusals return a bounded error object after rolling back the operation's subtransaction.

## Local setup and permissions

Apply all migrations using the established trusted-operator process, then apply `database/review_runtime_grants.sql` with the existing `runtime_role` variable, after earlier grant scripts. No automatic migration, production credential or retained database change is performed by this phase.

The application receives SELECT on teacher history and EXECUTE on two narrowly scoped functions. It does not gain direct INSERT/UPDATE/DELETE on releases or teacher events, nor assessment publication writes. The SECURITY DEFINER functions use fixed trusted schema paths; their callees put temporary schemas last to prevent shadow-table attacks. PUBLIC execution is revoked. As with the existing application services, the backend database credential is trusted and must not be distributed to end users; the API supplies authenticated account identity.

Dependencies and configuration are unchanged. No model weights, paid API, cloud service or additional runtime package. **Hardware-validated model selection: pending.** Real inference quality, native Windows PostgreSQL authentication, and multi-connection contention remain unvalidated. Tests use a disposable embedded PostgreSQL/pgvector adapter with an explicitly restricted role.

See [completion evidence](phase-13-completion.md). Next: Phase 14 assessment publication and reference codes.


## Phase 17 update

Confirmed feedback defects cannot be approved again in place. Open the version from Feedback review, inspect its evidence and save a corrected new version. Fresh verifier/validation reports and approval remain required. Acknowledging score review never restores the old release or changes prior scores. See [feedback](feedback.md).
