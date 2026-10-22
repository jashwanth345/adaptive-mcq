# Classroom assessments and reference codes — Phase 14

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Teachers can create fixed classroom assessments from their own courses and latest question versions, save drafts, permit registered students, publish, replace/revoke codes and close an assessment. Students can join with a valid code and see assessment metadata. **Taking an assessment, scoring and result release remain Phase 15.** The settings are stored now; no timer or score is simulated.

All components use the existing **FREE / OPEN SOURCE** local stack. No service, model, dependency, cloud fallback or subscription was added. Default mock generation remains usable for private drafts and cannot produce a publishable assessment.

## Teacher workflow

1. Create a course in the teacher workspace and generate/review question drafts.
2. Open **Assessments → Create assessment**, select the course and questions, then save. Drafts can hold pending or test questions, but publication stays blocked.
3. Set the time limit (blank for untimed, or 1–240 minutes), maximum attempts (1–100), question/option randomization and result-release policy. Select up to 50 questions; selection order sets fixed order, with one point per item.
4. Add permitted students by their registered email. No invitation or email is sent. Up to 200 student records are allowed per assessment. Remove/restore access without deleting history.
5. Before publication, every selected version must still be current, source-grounded, approved by this teacher and backed by fresh passing verifier/validation evidence. Mock origin, rejection, quarantine, edited versions, changed duplicate-comparison corpus or later unapproved validation reports block publication. Generate the question set before performing the final checks/approvals.
6. Choose a code expiry of 1–720 hours (default 24), select **Publish assessment**, then confirm. Publication, initial code issuance, operation history and audit entry commit together. Failed checks leave the assessment a draft.
7. Copy the displayed code and share it yourself with permitted students. The code is returned on issuance and successful retry of that same request, not on ordinary detail reads. Leaving/reloading the page hides it. Issue a replacement if needed.

Published questions, settings and ordering are immutable. Replacement revokes earlier codes; students must rejoin with the replacement before a new attempt. Revocation blocks new access without closing the assessment. Closing is permanent and revokes all codes. Existing admissions/attempts remain stored. Participant permissions can change while an assessment is open.

## Student workflow

Open **Join assessment**, enter the teacher's code and submit. The student must be signed in with a live student role and listed as an active participant. The assessment, teacher, code, expiry, remaining attempt allowance and current question release evidence are checked again. Knowing the code or belonging to the course alone is insufficient.

A successful join stores an admission and active course membership; repeated joins to the same code do not duplicate admissions/audit events. It does not create an attempt. The response and joined-assessment list contain only title, count, settings and availability. They never contain stems, options, answer keys, explanations or teacher source documents. Previously admitted metadata remains visible when access is revoked, with an unavailable label.

Wrong, expired, revoked, unauthorized and unavailable codes return the same generic message. A persistent account limit permits ten code checks per 60-second window; the eleventh returns 429 with `Retry-After: 60`. Rejected guesses are committed to the counter. Accounts must be registered first and existing authentication limits still apply. This is a local project account limiter, not a claim of internet-scale abuse resistance.

## Code storage and retries

Display format: `MCQ-XXXX-XXXX-XXXX-XXXX-XXXX` (example format, not an issued code). Twenty uppercase hexadecimal characters provide 80 secret-derived bits. A domain-separated HMAC-SHA-256 over teacher ID, request UUID and collision counter uses the existing server JWT secret. The normalized code's SHA-256 digest is stored, never plaintext. Case, spaces and hyphens are normalized on entry. Codes travel in POST bodies and issuance responses, not URLs, logs, local storage or audit payloads.

Each mutation requires an idempotency UUID. Owner/key reuse with a different request is a conflict. Draft saves/publication also require the current revision, preventing unnoticed overwrite. Same-key issuance retries recover the same code without storing plaintext. Up to four deterministic collision candidates are attempted; a collision rolls back the entire operation, including revocation of an earlier code. Replaying an issuance whose code has expired or been revoked does not return that code as active. Rotating the server secret prevents recovery of an old issuance through its old request; create a replacement using a new request key. Existing stored digests still validate their original codes until expiry/revocation.

Only the authenticated server chooses the owner. The database functions run with fixed schema paths and narrow grants. Teacher operations serialize under the existing owner lock; drafts use revision checks. All expected business refusals roll back their function subtransaction and return a bounded error code. Unexpected errors roll back the surrounding transaction. The application has no direct writes to assessment, participant, admission, operation or code tables. API reads are explicitly scoped to the account; this is not database row-level security or protection against compromise of the application DB credentials.

## API

All routes below begin `/api/v1`; authenticated responses use `Cache-Control: no-store`. Creation and mutation bodies reject unknown fields.

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/teacher/assessments` | Paginated owned list / create draft |
| GET | `/teacher/assessments/{id}` | Owned details, participants and code metadata |
| POST | `/teacher/assessments/{id}/save` | Revision-checked draft save |
| POST | `/teacher/assessments/{id}/publish` | Publish and issue initial code atomically |
| POST | `/teacher/assessments/{id}/rotate` | Revoke existing codes and issue replacement |
| POST | `/teacher/assessments/{id}/revoke` | Revoke codes |
| POST | `/teacher/assessments/{id}/close` | Close and revoke |
| POST | `/teacher/assessments/{id}/participants` | Allow/remove registered student by email |
| POST | `/student/assessments/join` | Check a code and store authorized admission |
| GET | `/student/assessments` | Paginated own admission metadata and current availability |

List limits are 1–24 with offset pagination. The UI uses six rows per page. Teacher detail includes the latest 20 code metadata records. Bodies are subject to the existing 16 KiB teacher/student request limit.

## Local setup and phase boundary

Apply all migrations with the established trusted local operator process, then apply [assessment_runtime_grants.sql](../database/assessment_runtime_grants.sql) with the existing `runtime_role`, after previous module grants. [Migration 007](../database/migrations/007_assessments.sql) adds revisions, operation records, participant permissions, admissions, guess counters and narrowly scoped functions. It preserves earlier scores, legacy assessments and private-practice rules. No automatic retained-database migration was performed.

New managed assessments are identified by the transactional publication operation record. Their database attempt-insert guard already requires a current authorized admission and reruns access checks; this prevents later code from relying on an old join alone. Historical pre-Phase-14 fixtures remain under their existing integrity rules. This phase exposes no attempt-create endpoint. Phase 15 must implement atomic start/resume, answer confidentiality, item/option snapshots, timing and result-release rules, and consistent lock ordering. Native PostgreSQL multi-connection races remain to be tested; embedded single-connection tests cannot validate them.

No native PostgreSQL/pgvector deployment, local LLM quality or hardware validation is claimed. Positive publication tests use synthetic evidence, never a mock-to-production approval bypass. The research presentation was not changed to imply measured results.


## Phases 15 and 16 update

After joining, students can start/resume the admitted assessment. Server deadlines, maximum attempts, pinned question/option order, saved progress, grading and result-release settings are now enforced through the attempt workflow. Existing admitted attempts may finish after code revocation/removal/closure until their original deadline; new starts remain blocked. Fixed classroom question sets never adapt. See [the combined workflow guide](attempts-and-adaptive.md).


## Phase 17 update

Confirmed feedback defects quarantine exact versions and pause new attempts containing them. Existing admitted attempts retain the Phase 15 completion boundary. Historical scores remain unchanged and under review; a late completion reopens the owner’s score-review task. Corrected versions belong in new assessments. See [feedback](feedback.md).
