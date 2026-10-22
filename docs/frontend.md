# Frontend setup and behavior

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

**Phase 13 update:** [Teacher review](teacher-review.md) adds an owned review queue, source inspection, immutable editing, version history and explicit rejection/approval. Mock questions remain ineligible after editing. Each new version needs fresh checks. Approval does not publish an assessment.

**Phase 12 update:** Draft studio includes a [Validation workspace](validation.md), saved blocker/check reports, private duplicate candidates and an unsaved exact-arithmetic preview. Test content cannot be released.

**Phase 11 update:** [Draft studio](generator.md) now includes a private [Verification workspace](verifier.md) with test reviews and saved report history for both roles. Reports remain advisory and cannot approve or publish questions. Independent-model verification is unvalidated. For memory-conscious browser checks, set `E2E_LIGHTWEIGHT=1`; this skips embedding/LLM inference but still uses real authentication, PDF extraction, database persistence and navigation with test generation and review.

Phase 5 delivers the web application foundation. Sign-in, student registration, account identity, password changes and sign-out use the existing backend. Teacher/student assessment tools and AI generation remain **Planned**.

Phase 6 adds the live [teacher dashboard and course/topic organization](teacher-dashboard.md), including an additional operator-applied permission script. The Phase 5 descriptions below remain the foundation baseline; teacher operational behavior is detailed in that guide.

Phase 7 adds the [student dashboard, attempt metadata and saved practice preference](student-dashboard.md), with its own narrow permission script. The student workspace no longer consists solely of planned-feature cards. Assessment attempts, scores, generation and adaptive mastery remain planned.

## Start on your laptop

The backend requires local PostgreSQL/pgvector, all current migrations (001–006), restricted runtime grant scripts for the implemented modules and private configuration from the [backend guide](backend.md) and [authentication guide](authentication.md). The frontend can load before that setup is complete, but registration and sign-in require a ready backend.

In one terminal, from the project root (`outputs/adaptive-mcq`):

```powershell
.\.venv\Scripts\python.exe -m backend.app
```

In a second terminal, from the same project root:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run dev
```

Open **http://localhost:5173**. The first dependency installation requires internet access. After installation, this frontend needs no online service, external font, CDN or subscription. Node.js 22.19.0 and npm 10.9.3 were used for verification. The lockfile fixes dependency versions. Ollama is not called by this phase.

To inspect the optimized build, stop the development server and run:

```powershell
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run preview
```

Both servers bind to localhost on port 5173 and fail if it is occupied. Preview is a local review server, not a public production deployment.

## API connection and configuration

Browser requests use same-origin `/api/v1/...` URLs. The Vite development/preview proxy forwards `/api` to `http://127.0.0.1:8000` by default. To use another local backend port, set this in `frontend/.env.local` and restart Vite:

```dotenv
LOCAL_API_ORIGIN=http://127.0.0.1:8000
```

Only HTTP loopback origins without credentials, paths, queries or fragments are accepted. This setting is read by the proxy rather than bundled into browser code. Never copy the backend `.env` into `frontend/`, or put secrets in `VITE_` variables. No cloud endpoint or paid fallback exists.

The backend default `FRONTEND_ORIGIN=http://localhost:5173` matches normal startup. A custom frontend port also needs its corresponding backend origin. The backend ignores forwarded client headers; local proxy requests share the loopback throttling bucket. This configuration is for one-computer use. Classroom network deployment needs a later deployment/security design.

## Screens and account rules

| Route | Delivered behavior |
|---|---|
| `/login` | Email/password sign-in, password visibility, progress and errors |
| `/register` | Student-only registration with password confirmation; separate sign-in after creation |
| `/workspace` | Default workspace: teacher when available, otherwise student |
| `/workspace/student` | Student workspace foundation with planned capabilities |
| `/workspace/teacher` | Teacher workspace foundation restricted by account roles |
| `/account` | Identity and roles, password change, sign out everywhere |
| Other paths | Recoverable page-not-found screen |

Teacher accounts require the [local operator commands](authentication.md). There is no public teacher-registration switch, default password or authentication bypass. Dual-role users can switch workspaces. Frontend role checks organize navigation; server permission checks remain authoritative. Future feature endpoints must enforce resource ownership as well as roles.

Tokens remain in memory and are not saved to cookies, localStorage or sessionStorage. Refreshing/closing a page loses its browser session, but does not revoke the server record. Use **Sign out** or **Sign out everywhere** for revocation; otherwise the server session expires according to its short-lived token policy. The frontend expires sessions automatically and rechecks identity when the page regains focus/visibility. Rejected tokens return the user to sign-in. There are no refresh tokens or automatic login retries.

If server sign-out fails, the app keeps the session and shows an error so revocation can be retried. It does not report false success. A successful password change revokes all sessions. An incorrect current password leaves a still-valid session usable after an identity recheck.

Registration/new passwords require 12–128 characters. Passwords are never trimmed; names and emails are trimmed. Registration does not submit a role field. Requests time out after 15 seconds, rate-limit responses explain the wait, and errors do not echo raw credentials.

## Interface and source

The interface uses navy, white and teal with purple accents, responsive navigation, local SVG/CSS artwork, system fonts, visible keyboard focus, labels, a skip link, status/error messages and reduced-motion support. Planned tools are descriptive cards, not working controls or fabricated dashboards. No questions, mastery percentages or evaluation results are displayed.

- `src/api.ts`: bounded requests, fixed API paths and safe error presentation.
- `src/auth.tsx`: in-memory identity, expiry, revalidation and session operations.
- `src/App.tsx`: routes, access guards and screens.
- `src/ui.tsx` / `src/styles.css`: reusable components and responsive styling.
- `local-origin.ts` / `vite.config.ts`: local proxy and build configuration.

## Dependencies — FREE / OPEN SOURCE

React/React DOM, React Router, Vite, Tailwind CSS, TypeScript, Vitest, Testing Library, jsdom and Playwright are free/open-source and installed locally. Exact versions are in `frontend/package.json` and its lockfile. TypeScript checks contracts at build time; it needs no runtime service. Browser tests used installed Chrome; a compatible local Chromium or Edge executable can also be selected. No API key, payment card or paid product is required.

## Reproduce validation

From the project root:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

Browser integration also requires the Phase 4 Python environment and the existing test-only database adapter dependencies:

```powershell
npm.cmd --prefix database/tests ci
```

`tests/e2e.mjs` starts a temporary backend, built-frontend preview and disposable PostgreSQL on local ports. It creates a synthetic student, exercises the actual authentication API, captures desktop/mobile screenshots and stops child services in `finally`. Run the build first. The fixture is not an application database fallback and does not provision retained accounts.

The Windows runner defaults to `.venv/Scripts/python.exe` and installed Chrome, then Edge. Override `TEST_PYTHON` or `E2E_BROWSER` with existing executables when needed. Without a detected browser it uses Playwright's locally installed Chromium. `E2E_OUTPUT` changes the screenshot directory; the default is ignored `frontend/test-results/`. Run with clean test settings, not real database credentials.

See the [completion record](phase-5-completion.md) for actual results and remaining limitations. Passing software tests does not establish MCQ quality or learning effectiveness.
## Phase 8 addition

The authenticated `/materials` route and **Study materials** navigation item are shared by teacher and student accounts. It supports a bounded raw-PDF upload, private paginated library, duplicate notification, source page navigation, empty-page warnings and plain-text previews. See [materials.md](materials.md) for API contracts, storage rules and current limitations. No frontend dependency was added. PDF requests use a 60-second client timeout; existing JSON requests retain 15 seconds. Tokens remain in memory.

## Phase 9 addition

The selected PDF now has a local source-search panel: index coverage/status, **Prepare for search**, topic input, cited source excerpts, original-page navigation and explicit unavailable/busy/insufficient-evidence states. Model operations have a 210-second client timeout; model subprocesses have a 180-second limit. Normal JSON requests retain the prior timeout. Read [rag.md](rag.md) before enabling native use. The shared API keeps fixed local routes and in-memory bearer tokens. No frontend library was added. Browser tests now require the explicitly prepared local embedding model and exercise real CPU inference; screenshots remain synthetic development evidence.

## Phase 14 navigation update

Teacher accounts now have an **Assessments** page for drafts, publication, participant permissions and reference-code controls. Student accounts have **Join assessment** for authorized code entry and metadata previews. Existing dashboards continue to display stored counts/history. Attempts and scoring are Phase 15. See the [assessment guide](assessments.md).


## Phases 15 and 16 update

Student navigation now includes My learning and links into the attempt player. The player supports saved choices/flags, stable order, countdown, explicit submission, released results and source excerpts. The learning page shows evidence coverage, a provisional index and eligible private practice. Desktop/mobile behavior and the real local API flow are covered by `frontend/tests/attempt-e2e.mjs`. See [the combined workflow guide](attempts-and-adaptive.md).


## Phase 18 update

My analytics and Classroom analytics provide counts, score/time summaries, topic/difficulty/type breakdowns, feedback signals and paginated history. Individual classroom assessments include most-missed questions and an optional teacher-only ranking. No sample performance values appear in empty screens. See [metric and visibility definitions](analytics.md).

## Phase 17 update

Completed attempts now offer per-question issue reports and helpful/poor ratings. My feedback provides private report history. Feedback review provides an owned queue, explicit confirmation, score-review acknowledgement and links to correction workflows. See [the feedback guide](feedback.md).


## Phase 19 update

Teacher navigation now includes Evaluation lab: saved synthetic checks, evidence/review downloads and a separate consent-confirmed private study export. Research metrics remain To be evaluated. See [evaluation workflow](evaluation.md).
