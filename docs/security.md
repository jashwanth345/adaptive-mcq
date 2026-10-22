# Local application security

**16 October local-workspace change:** public signup now offers new Teacher and Student accounts. Separate fixed-role database functions create new identities only; neither endpoint can promote an existing user or accept an arbitrary role. Teachers remain confined to their own materials, courses, assessments and authorized student results. This local self-service role policy is not institutional teacher identity verification.

Phase 21 hardens the existing one-computer application. The core remains FREE / OPEN SOURCE and local; advisory lookups are development-time checks, not runtime dependencies. No paid security service is required.

## Scope and trust boundaries

The supported deployment is a trusted Windows user running the frontend, FastAPI, PostgreSQL and optional guarded Ollama locally. Teachers and students have distinct authenticated application permissions. Uploaded text, names, feedback, model responses, browser origins and request bodies are untrusted.

The review covers unauthorized API use, cross-account access, unexpected browser origins, oversized/slow bodies, sensitive HTTP caching, stored HTML-like input, upload handling and known package advisories. This is not a penetration-test certification or a guarantee that all vulnerabilities have been found. A malicious OS administrator or process with access to project secrets/database files is outside this application boundary.

## HTTP and browser controls

| Boundary | Implemented behavior |
|---|---|
| Backend binding / Host | Local loopback configuration; only localhost/loopback Host names accepted; duplicate Host rejected; forwarded headers do not grant identity |
| Browser Origin | Reject null, duplicate and unexpected Origin values with 403 before reading the body or running application logic; allow the configured frontend and the backend's same origin |
| CLI requests | An absent Origin remains supported; this never replaces bearer authentication or ownership checks |
| CORS | Only the configured frontend receives cross-origin response access; no credential cookies or wildcard origins |
| JSON/API body | All `/api/` routes default to 16 KiB, including feedback review and future routes; actual streamed bytes are counted; malformed/duplicate/dishonest Content-Length is rejected |
| Slow JSON body | A total 15-second receive deadline returns safe 408; this is not a generation or evaluation execution timeout |
| Body encoding | Compressed JSON request bodies are rejected with 415; the server does not decompress an unlimited request |
| Private responses | All API responses use `Cache-Control: no-store`, including successful feedback responses and errors |
| Browser headers | `nosniff`, `DENY` framing, `no-referrer` and disabled camera/microphone/geolocation permissions |
| Built frontend preview | CSP permits same-origin scripts/connections and forbids objects, framing and base-URL replacement; inline scripts/eval are not allowed |
| Development frontend | Shares framing/referrer/type protections and disables cross-origin asset reads; no strict script CSP because React hot refresh injects inline development code |

The preview permits inline **styles** for UI styling, not inline scripts. Local `/docs` keeps its existing self-contained inline documentation script/style policy; its framing and referrer protections still apply. These are explicit policy differences, not a claim that every response uses the same CSP. Vite preview remains a local development/demo tool, not a public production server.

An Origin header is a browser boundary, not proof of user identity; non-browser clients can omit or forge it. CORS alone does not prevent a request from executing, which is why explicit Origin rejection was added. `no-store` controls compliant HTTP caches, not malicious extensions, user exports or an application-managed Cache API. The app does not persist bearer tokens in browser storage or use service-worker caches.

## Authentication, roles and private records

- Argon2id password hashing, bounded hash concurrency, generic login failures, persistent login/registration throttling and short-lived signed JWTs remain in place.
- JWT algorithm, issuer, audience, required claims, timestamps and identifiers are validated. Sessions must also be active and unexpired in the database. Roles are read from the database on each protected request.
- Registration cannot grant a teacher role. Logout, logout-all and password change revoke sessions. The browser holds tokens only in memory and sends them only in Authorization headers to allowlisted same-origin API paths.
- Material, source, question-version, assessment, attempt, feedback and evaluation access is scoped by authenticated identity. SQL parameters are bound; browser-supplied owner IDs never become authority.
- Classroom publication still requires real eligible evidence. A synthetic fixture used by tests never makes ordinary mock drafts publishable.

The route-wide negative test enumerates all 65 protected OpenAPI operations and checks missing/invalid bearer rejection before database use (130 requests). Existing integration suites separately check valid sessions, incorrect roles, foreign objects, revoked sessions, immutable versions and database runtime privileges. Native PostgreSQL grants/authentication and independent-connection concurrency still need deployment verification.

## PDF boundary

PDF uploads retain their separate authenticated streaming path, **5 MiB** byte limit, 15-second receive deadline and 30-second extraction worker timeout. Declared oversized uploads are rejected before a file is created; actual streamed bytes are always checked. Length mismatches remove temporary files and release the processing slot. Existing failure tests cover malformed/encrypted/blank/overlarge PDFs, private library access and duplicate reuse.

Only server-generated random filenames are used inside the local upload directory. Redirected directories are refused, document signatures are checked and extraction preserves source pages. PDFs are not served as active browser content; the UI renders extracted text. The parser runs in a subprocess with page/text limits. This subprocess is **not** a full operating-system sandbox or malware scanner. File permissions, backup access and native deployment remain operational responsibilities.

## Dependencies and repeatable checks

The initial OSV lookup identified `setuptools==78.1.0`. Its PackageIndex download traversal is addressed in 78.1.1; a separate macOS source-distribution exclusion issue is addressed in 83.0.0. The pin and local environment were updated to **83.0.0**, without changing model packages. The macOS issue is not a demonstrated Windows application exploit. See the maintainer advisories: [PackageIndex traversal](https://github.com/pypa/setuptools/security/advisories/GHSA-5rjg-fvgr-3xxf) and [source-distribution exclusion](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c).

On 14 October 2026, the repeat OSV batch lookup of the **65 installed versions pinned in backend/requirements.txt** returned no advisory matches or remaining result pages. This excludes Python itself, the browser, Ollama binaries, model weights, OS components and development-only Python packages. npm audits of the frontend and disposable database-test lockfiles also returned zero reported advisories. See the [saved audit evidence](evidence/phase-21-dependency-audit.json). Package metadata lookups and `pip check` do not prove absence of vulnerabilities or model-inference compatibility.

From the project root, using the existing environment and a writable temporary directory:

```powershell
$env:MCQ_RUN_DB_TESTS = '1'
$env:MCQ_RUN_MODEL_TESTS = '0'
$env:NODE_OPTIONS = '--max-old-space-size=256'
$env:RAYON_NUM_THREADS = '2'
$env:TEST_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
$env:E2E_LIGHTWEIGHT = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
npm.cmd --prefix frontend test -- --pool=threads
npm.cmd --prefix frontend run build
node frontend/tests/e2e.mjs
npm.cmd --prefix frontend run test:integration
npm.cmd --prefix frontend audit
npm.cmd --prefix database/tests audit
```

Browser suites should run sequentially on this 8 GB laptop. The networked package audits are optional repeat checks and require internet access; the application runtime does not. OSV's batch API was queried with only public package names/versions, not source, secrets or student records. Do not use automatic force-upgrade commands without checking compatibility.

## Remaining limits

Phase 22 subsequently verified native database authentication and restricted grants, private Windows file permissions, bounded independent-transaction contention, database restart recovery, separate application/PDF restore and prepared local startup. See the [Phase 22 evidence](phase-22-completion.md). Full-machine/power-loss recovery and physically disconnected operation remain untested. Public internet deployment, HTTPS termination, MFA, email ownership verification, password-recovery delivery, distributed throttling and comprehensive denial-of-service protection are not implemented. The origin/size/time controls reduce particular risks; they are not a global connection/concurrency quota. Registration conflict status still reveals account availability.

Hardware-validated model selection, independent-model quality, broad mathematical correctness and learner benefit remain **To be evaluated**. No real LLM inference or paid service was introduced in Phase 21.

Guidance used during review: [OWASP REST security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), [HTTP headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html), and [file uploads](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html). These inform the controls; they do not constitute compliance certification.
