# Phase 14 — assessment publication and reference codes

Deliver teacher assessment authoring with owned course/question-version selection, revision-safe draft saves, explicit publication, expiry/rotation/revocation, closing and a participant allowlist. Publish and initial code issuance are atomic; current approval/validation gates remain mandatory. Test-origin content cannot publish.

Authenticated students may enter a code to join an allowed assessment and read a metadata-only preview. Codes do not enroll arbitrary students: teachers must first permit their registered email. Successful joins record admissions and course membership; no question answers or private source text are returned. Code validation is rate limited in the database. Expiry, revocation, publication, participants, remaining attempts and question eligibility are rechecked. Attempt creation/scoring remains Phase 15, with a database guard already protecting newly managed assessments.

Use a forward migration and restricted runtime functions. Reference codes use a domain-separated HMAC of the request UUID and owner under the existing server secret (80-bit displayed value), with uniqueness/collision retries; only SHA-256 digests are stored. This allows retry recovery without storing plaintext codes. Secret rotation requires issuing a new code if an old issuance cannot be recovered.

No new runtime dependencies, cloud services or model inference. Verify restricted-role APIs and SQL, frontend behavior, a lightweight real-browser draft/blocked-publication flow, and synthetic eligible publication/join tests. Preserve legacy records; document native-database concurrency limitations. Stop after Phase 14.
