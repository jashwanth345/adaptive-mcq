# Phase 21 — security hardening

**Complete: 15 October 2026.** Verification ran on 14–15 October 2026 using lightweight synthetic fixtures. **21 of 24 roadmap phases are complete; three remain.**

## Delivered changes

- **Feedback privacy and request limits:** replaced incomplete route-prefix lists with API-wide no-store and non-upload body limits. Successful feedback-review responses can no longer opt into HTTP caching, and feedback decisions receive the same size protection as other API writes.
- **Browser request boundary:** unexpected/null/duplicate Origin values are rejected before body reads or application handling. Configured frontend, same-origin local documentation and authenticated CLI use remain supported. Duplicate Host is rejected and forwarded host headers do not authorize origins.
- **Bounded request handling:** 16 KiB for streamed non-upload API bodies, a total 15-second receive deadline, declared/actual length validation and rejection of compressed JSON bodies. Errors use safe codes and do not echo private payloads.
- **PDF upload checks:** declared oversize rejected before file creation; length mismatches clean up files and release the processing slot. Existing authenticated streaming, byte/page/text limits, isolated extraction and owner-scoped previews remain enforced.
- **Browser policies:** built frontend preview gets same-origin script/connect CSP, no inline script/eval, framing protection, no-referrer, nosniff and disabled camera/microphone/geolocation. Development refresh keeps its documented policy exception; both Vite modes disable cross-origin asset reads.
- **Dependency remediation:** updated only `setuptools`, from 78.1.0 to 83.0.0, addressing the two advisory families returned by OSV. The download was approximately 1 MB; no model packages, weights or paid services were added.
- **Evidence:** added 24 security-boundary cases, an API-wide missing/invalid bearer matrix, upload assertions and browser checks for policy headers, inert stored HTML-like names and policy violations.

See the [security guide](security.md), [phase scope](phase-21-plan.md) and [saved public dependency-audit evidence](evidence/phase-21-dependency-audit.json).

## Verification

| Check | Result |
|---|---|
| Focused security/API/token checks | **55 passed**; overlaps the full backend suite |
| Protected-operation matrix | **65 operations × 2 credential cases** rejected before database use; part of the focused/full suites |
| Full backend regression | **288 passed, 1 skipped**; the skipped check requires a prepared real embedding model |
| Final upload recheck | **7 passed** after the final assertion was added, including a streamed oversized upload without Content-Length; overlaps the backend suite |
| Frontend regression | **115 passed** across 15 files |
| Production frontend build | Passed |
| Python lint/formatting | Passed; 98 backend/evaluation files checked |
| Foundation browser with security checks | **51 passed**; headers present, stored HTML-like name inert, no runtime errors/external requests/CSP violations |
| Classroom browser journey | **14 passed**, including API restart, lost-response retry, feedback/quarantine, mastery, analytics and study export |
| Python dependency compatibility | `pip check` passed after the upgrade |
| Backend advisory lookup | **65 pinned installed packages**, zero final OSV matches and no remaining result pages |
| npm advisory audits | Zero reported advisories for frontend and disposable database-test lockfiles |

The first route-matrix implementation inspected FastAPI's lazy route list and found no concrete operations; it was corrected to enumerate the generated OpenAPI schema before the passing run. The initial package installation hit restricted default temporary storage, so it was retried in writable workspace temporary storage. Regression runs use the successfully updated environment. The existing Starlette/httpx deprecation warning remains.

Counts are software checks, not research accuracy results, and overlapping suites must not be added into a study sample size. No actual learner data or AI inference was used. The SQL schema and grants were not changed; the separate 119-check SQL-suite result remains Phase 20 evidence, while current backend integrations recheck relevant API/database behavior.

## Remaining boundaries

Native PostgreSQL authentication/grants, independent concurrent connections, OS file permissions, durable recovery and complete prepared offline startup remain Phase 22 work. Vite preview is a local demo tool. This phase does not certify a public-internet deployment or protect against a malicious local administrator. Per-request resource limits are not complete denial-of-service protection; account availability remains observable through registration conflicts.

The default generator/verifier remain **mock**, and ordinary mock content remains unpublishable. Hardware-validated model selection, actual AI quality and learning benefits are still **To be evaluated**. The core stays local and free.

## Handoff

Next is **Phase 22 — local deployment and recovery**, followed by Phase 23 final documentation and Phase 24 final evidence/presentation updates. Phase 22 has not started. See [current project progress](project-progress.md) for feature boundaries and earlier deferrals.
