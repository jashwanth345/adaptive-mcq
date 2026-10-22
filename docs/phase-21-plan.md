# Phase 21 — security hardening

Authorized 14 October 2026. Scope: review and harden the existing local application, with lightweight synthetic tests. No model inference, paid service, account changes or Phase 22 deployment work.

## Confirmed gaps and planned changes

- Replace route-prefix lists for sensitive caching and JSON body limits with API-wide defaults; feedback-owner routes currently fall outside both lists.
- Reject disallowed/null browser origins before request handling, while preserving the configured frontend, same-origin local API documentation and non-browser clients without Origin.
- Bound JSON body read time as well as bytes; reject malformed/ambiguous length headers and unsupported body encodings without reflecting submitted data.
- Keep uploads authenticated, streamed, size-limited and separately timed. Reject declared oversized PDFs before creating a file; verify cleanup and private ownership.
- Apply browser security headers to the frontend preview, including a restrictive script policy, framing restrictions and no-referrer. Keep development hot reload functional and distinguish development from preview.
- Recheck all protected API routes for missing/invalid bearer tokens, existing role/ownership tests, token validation, upload handling and safe failure responses.
- Review public dependency advisories where available; report scanner coverage honestly. Do not automatically upgrade packages or claim certification.

## Verification and handoff

Focused middleware/security regressions, backend suite, frontend/build checks and both connected browser journeys under the hardened headers. Test raw ASGI streams for over-limit and stalled bodies without large memory allocation. Use disposable database fixtures and small workers. Record concrete fixes, coverage, residual limits and the next phase in a completion report.

The local design does not protect against a malicious operating-system administrator. Native PostgreSQL permissions/authentication/concurrency and durable deployment remain Phase 22 work. Real model quality and hardware validation remain deferred.
