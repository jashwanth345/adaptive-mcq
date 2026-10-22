# Phase 5 — frontend foundation

Authorized by the user on 5 October 2026. This record precedes implementation.

Objective: build a responsive, accessible local web interface for the existing authentication API and establish reusable application navigation. Teacher assessment management and student practice dashboards belong to phases 6 and 7.

## Files and architecture

- `frontend/`: React, TypeScript, Vite and Tailwind application; pinned npm lockfile.
- `frontend/src/`: API client, in-memory authentication provider, route guards, sign-in/registration, workspace foundation, account security, reusable styles and components.
- `frontend/tests/`: behavioral unit/component tests and real-browser integration checks.
- `docs/frontend.md` and `docs/phase-5-completion.md`: setup, verified behavior and limitations.
- README: current phase and local startup instructions.

No database migration, new backend route, model download, paid service or cloud deployment is required. The frontend uses the existing versioned authentication and role API. Backend permission checks remain authoritative. A local development/preview proxy forwards `/api` to the loopback backend. Backend secrets stay outside the frontend; only an explicitly named public local endpoint may configure the proxy.

Session tokens exist only in application memory. Reloading or closing the page ends the browser session; server expiry/revocation remain separate. Registration creates student accounts only. Teacher accounts continue to require the existing local operator command. Future assessment/AI functions display Planned without fabricated scores or functionality.

## Dependencies and checks

FREE / OPEN SOURCE: React, React DOM, React Router, Vite, TypeScript, Tailwind CSS, Vitest, Testing Library, jsdom, Playwright. Dependencies are project-local; the browser test runtime is a development tool only.

Check strict types and production build; test API errors, route/role guards, session expiry, logout and account flows; run real browser flows against the existing backend with disposable PostgreSQL; inspect desktop/mobile layouts. Test fixtures are synthetic and must not become demo results or real accounts. Native PostgreSQL setup remains a separate outstanding deployment check.
