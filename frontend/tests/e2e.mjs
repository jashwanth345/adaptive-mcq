// Real-browser checks against the existing backend and a disposable PostgreSQL fixture.
// Synthetic users/database only. E2E_LIGHTWEIGHT=1 skips embedding inference;
// generator always uses the labelled deterministic test fixture.
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { createInterface } from 'node:readline';
import { mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const frontend = fileURLToPath(new URL('..', import.meta.url));
const root = path.resolve(frontend, '..');
const output = process.env.E2E_OUTPUT || path.join(frontend, 'test-results');
mkdirSync(output, { recursive: true });
const children = []; let browser; let passed = 0;
const python = process.env.TEST_PYTHON || path.join(root, '.venv', 'Scripts', 'python.exe');
function start(command, args, env = {}) {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, ...env }, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  let logs = ''; child.stdout.on('data', data => { logs = (logs + data).slice(-5000); }); child.stderr.on('data', data => { logs = (logs + data).slice(-5000); }); child.logs = () => logs; children.push(child); return child;
}
async function port() { const server = createServer(); server.listen(0, '127.0.0.1'); await once(server, 'listening'); const p = server.address().port; await new Promise(resolve => server.close(resolve)); return p; }
async function waitReady(url, child) {
  const deadline = Date.now() + 60000; let lastHealth = 'No response';
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Server exited: ${child.logs()}`);
    try { const result = await fetch(url, { signal: AbortSignal.timeout(2000) }); if (result.ok) return; if (url.endsWith('/health/ready')) lastHealth = await result.text(); } catch {}
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  throw new Error(`Server not ready: ${url}\n${lastHealth}\n${child.logs()}`);
}
const check = text => { passed++; console.log(`PASS ${passed}: ${text}`); };
try {
  const pg = start(process.execPath, [path.join(root, 'database/tests/backend-server.mjs'), 'teacher'], { TEST_PYTHON: python });
  const lines = createInterface({ input: pg.stdout });
  const [line] = await Promise.race([once(lines, 'line'), new Promise((_, reject) => { const timer = setTimeout(() => reject(new Error('PostgreSQL fixture startup timed out')), 45000); timer.unref(); })]);
  lines.close(); const dbPort = new URL('postgres://' + JSON.parse(line).connection).port;
  const apiPort = await port(); const webPort = await port(); const origin = `http://localhost:${webPort}`;
  const api = start(python, ['-m', 'backend.tests.browser_app'], {
    APP_ENV: 'test', API_HOST: '127.0.0.1', API_PORT: String(apiPort), FRONTEND_ORIGIN: origin,
    DATABASE_HOST: '127.0.0.1', DATABASE_PORT: dbPort, DATABASE_NAME: 'postgres', DATABASE_USER: 'postgres',
    DATABASE_PASSWORD: 'fixture-only-password', JWT_SECRET: 'fixture-only-secret-not-for-real-use-12345', DATABASE_POOL_SIZE: '1',
    AUTH_LOGIN_ACCOUNT_LIMIT: '10', AUTH_LOGIN_IP_LIMIT: '100',
    GENERATOR_MODE: 'mock',
    VERIFIER_MODE: 'mock',
  });
  await waitReady(`http://127.0.0.1:${apiPort}/api/v1/health/ready`, api);
  const web = start(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), 'preview', frontend, '--host', 'localhost', '--port', String(webPort), '--strictPort'], { LOCAL_API_ORIGIN: `http://127.0.0.1:${apiPort}` });
  await waitReady(origin, web);
  const executable = process.env.E2E_BROWSER || ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
  browser = await chromium.launch({ headless: true, ...(executable ? { executablePath: executable } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  context.setDefaultTimeout(20000);
  const policyViolations = [];
  await context.exposeBinding('__recordPolicyViolation', (_source, directive) => policyViolations.push(directive));
  await context.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', event => window.__recordPolicyViolation(event.effectiveDirective));
  });
  const page = await context.newPage(); const errors = []; const external = [];
  page.on('pageerror', error => errors.push(error.message)); page.on('request', req => { if (!req.url().startsWith(origin)) external.push(req.url()); });
  await page.goto(origin);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Personalized practice.');
  await page.screenshot({ path: path.join(output, 'landing-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'landing-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('link', { name: 'Login', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  check('Public landing page and login navigation work on desktop and mobile');
  const documentResponse = await page.goto(origin + '/account'); await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  const securityHeaders = documentResponse.headers();
  expect(securityHeaders['content-security-policy']).toContain("script-src 'self'");
  expect(securityHeaders['content-security-policy']).not.toContain("script-src 'self' 'unsafe-inline'");
  expect(securityHeaders['x-frame-options']).toBe('DENY');
  expect(securityHeaders['referrer-policy']).toBe('no-referrer');
  check('Built frontend delivers strict script policy, framing protection and no-referrer headers');
  await page.screenshot({ path: path.join(output, 'login-desktop.png'), fullPage: true }); check('Protected deep link redirects to sign-in; desktop screen rendered');
  await page.getByRole('link', { name: 'Create teacher or student account' }).click();
  const hostileName = 'Review <img src=x onerror=window.__unexpectedScript=1>';
  await page.getByLabel('Full name').fill(hostileName); await page.getByLabel('Email address').fill('review.student@example.com');
  await page.getByLabel('Password', { exact: true }).fill('fixture-pass-12345'); await page.getByLabel('Confirm password', { exact: true }).fill('fixture-pass-12345');
  await page.getByRole('button', { name: 'Create student account' }).click(); await expect(page.getByRole('heading', { name: 'You’re ready to sign in' })).toBeVisible(); check('Student registration persisted through the real backend');
  await page.getByRole('button', { name: 'Continue to sign in' }).click();
  async function signIn(password = 'fixture-pass-12345') {
    await page.getByLabel('Email address').fill('review.student@example.com'); await page.getByLabel('Password', { exact: true }).fill(password); await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Welcome, Review.' })).toBeVisible();
  }
  await signIn(); await expect(page.getByRole('link', { name: 'Teacher dashboard' })).toHaveCount(0); check('Sign-in opens the student workspace using database roles');
  await expect(page.getByText(hostileName, { exact: true })).toHaveCount(2);
  await expect(page.locator('.sidebar-user').getByText(hostileName, { exact: true })).toBeVisible();
  await expect(page.locator('.topbar-identity').getByText(hostileName, { exact: true })).toBeVisible();
  expect(await page.locator('img[src="x"]').count()).toBe(0);
  expect(await page.evaluate(() => window.__unexpectedScript)).toBeUndefined();
  check('Stored HTML-like account name renders as text and cannot create an executable element');
  await expect(page.getByLabel('Enrolled courses: 0', { exact: true })).toBeVisible(); await expect(page.getByText('No enrolled courses yet')).toBeVisible(); await expect(page.getByText('Your learning history starts here')).toBeVisible(); check('Student overview loads actual empty course and attempt records');
  await page.getByRole('radio', { name: 'Easy', exact: true }).focus(); await page.keyboard.press('ArrowRight'); await expect(page.getByRole('radio', { name: 'Medium', exact: true })).toBeChecked(); await page.getByRole('button', { name: 'Save preference', exact: true }).click(); await expect(page.getByText('Practice preference saved.')).toBeVisible(); await page.getByRole('button', { name: 'Refresh dashboard', exact: true }).click(); await expect(page.getByRole('radio', { name: 'Medium', exact: true })).toBeChecked(); check('Keyboard-selected practice preference saves through the backend and survives refresh');
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'student-desktop.png'), fullPage: true });
  const fixturePdf = spawnSync(python, ['-c', 'import sys; from backend.tests.test_materials import pdf_bytes; sys.stdout.buffer.write(pdf_bytes(("Database normalization source", "Transactions preserve consistency")))'], { cwd: root, windowsHide: true, timeout: 30000 });
  expect(fixturePdf.status).toBe(0);
  await page.getByRole('link', { name: 'Study materials', exact: true }).click();
  await expect(page.getByText('Your library starts here')).toBeVisible();
  await page.getByLabel('Material title', { exact: true }).fill('Database study notes');
  await page.getByLabel('Choose PDF', { exact: true }).setInputFiles({ name: 'notes.pdf', mimeType: 'application/pdf', buffer: fixturePdf.stdout });
  await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
  await expect(page.getByText('PDF saved. Extracted text is ready to review.')).toBeVisible({ timeout: 45000 });
  await expect(page.getByText('Database normalization source', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.getByText('Transactions preserve consistency', { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'materials-desktop.png'), fullPage: true });
  check('Student PDF uploads through real extraction/storage and previews original page two');
  await page.getByLabel('Material title', { exact: true }).fill('Same notes');
  await page.getByLabel('Choose PDF', { exact: true }).setInputFiles({ name: 'notes.pdf', mimeType: 'application/pdf', buffer: fixturePdf.stdout });
  await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
  await expect(page.getByText('This PDF is already in your library. Opened the existing material.')).toBeVisible({ timeout: 45000 });
  await expect(page.getByText('1 processed document', { exact: true })).toBeVisible(); check('Duplicate upload reuses the same private material');
  if (process.env.E2E_LIGHTWEIGHT !== '1') {
  await page.getByRole('button', { name: 'Prepare for search', exact: true }).click();
  await expect(page.getByText('Ready to search', { exact: true })).toBeVisible({ timeout: 200000 });
  await expect(page.getByText('2 of 2 passages indexed', { exact: true })).toBeVisible();
  check('Local CPU embedding model indexes both PDF passages in pgvector');
  await page.getByLabel('Topic or question', { exact: true }).fill('database normalization');
  await page.getByRole('button', { name: 'Find passages', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Retrieved source passages', exact: true })).toBeVisible({ timeout: 200000 });
  await expect(page.locator('.retrieved-sources .source-chunk').first()).toContainText('Database normalization source');
  await page.getByRole('button', { name: 'View source page 1', exact: true }).click();
  await expect(page.getByText('Page 1 of 2', { exact: true })).toBeVisible();
  await page.locator('.source-search').screenshot({ path: path.join(output, 'rag-desktop.png') });
  check('Real semantic search returns a page-cited source and opens its PDF page');
  }
  await page.setViewportSize({ width: 390, height: 844 }); await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(output, 'materials-mobile.png'), fullPage: true });
  await page.locator('.source-search').screenshot({ path: path.join(output, 'rag-mobile.png') });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  check('Material upload, library and page preview fit the mobile viewport');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('link', { name: 'Continue to questions', exact: true }).click();
  await expect(page.getByText('Test mode — no AI inference', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Source document', exact: true })).not.toHaveValue('');
  await page.getByLabel('Draft topic', { exact: true }).fill('normalization');
  await expect(page.getByLabel('Number of questions').locator('option')).toHaveCount(21);
  await page.getByLabel('Number of questions').selectOption('30');
  await expect(page.getByRole('button', { name: 'Generate 30 MCQs', exact: true })).toBeDisabled();
  await page.screenshot({ path: path.join(output, 'question-count-readiness.png'), fullPage: true });
  check('Question count supports 10–30 and test mode cannot masquerade as a real AI batch');
  await page.getByRole('button', { name: 'Create test draft', exact: true }).click();
  await expect(page.getByText('Test draft — not AI-generated', { exact: true })).toBeVisible();
  await expect(page.getByText('1 private draft', { exact: true })).toBeVisible();
  await expect(page.locator('.draft-options li')).toHaveCount(4);
  await expect(page.locator('.draft-evidence')).toContainText('Database normalization source');
  await expect(page.getByRole('button', { name: /Publish|Approve/ })).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'draft-studio-desktop.png'), fullPage: true });
  check('Student creates a labelled private test draft from the selected PDF without LLM inference');
  await page.getByRole('button', { name: 'Run test review', exact: true }).click();
  await expect(page.getByText('Test report · AI quality not evaluated', { exact: true })).toBeVisible();
  await expect(page.getByText('Publication status: not approved', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open test report 1', exact: true })).toBeVisible();
  check('Student persists a labelled non-AI review without approving the question');
  await page.getByRole('button', { name: 'Run validation', exact: true }).click();
  await expect(page.getByText('Release blocked', { exact: true })).toBeVisible();
  await expect(page.getByText('Test-generated content cannot be released.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open validation 1', exact: true })).toBeVisible();
  check('Student saves deterministic checks while test content remains blocked from release');
  await page.getByText('Try the arithmetic checker', { exact: true }).click();
  await page.getByRole('button', { name: 'Load arithmetic example', exact: true }).click();
  await page.getByRole('button', { name: 'Check arithmetic', exact: true }).click();
  await expect(page.getByText('Arithmetic preview: pass', { exact: true })).toBeVisible();
  await page.getByLabel('Math option B', { exact: true }).fill('8/2');
  await page.getByRole('button', { name: 'Check arithmetic', exact: true }).click();
  await expect(page.getByText('Arithmetic preview: fail', { exact: true })).toBeVisible();
  check('Arithmetic preview computes exact answers and rejects equivalent options without saving approval');
  await page.getByText('Try the arithmetic checker', { exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'review-desktop.png'), fullPage: true });
  await page.getByRole('link', { name: 'Student dashboard', exact: true }).click();
  await page.getByRole('link', { name: 'Generate MCQs', exact: true }).click();
  await page.getByRole('button', { name: 'Open test draft: normalization' }).click();
  await expect(page.getByText('Test draft — not AI-generated', { exact: true })).toBeVisible();
  check('Saved draft reopens from database after navigation');
  await expect(page.getByText('Test report · AI quality not evaluated', { exact: true })).toBeVisible();
  check('Saved review report reopens with the exact draft after navigation');
  await expect(page.getByRole('button', { name: 'Open validation 1', exact: true })).toBeVisible();
  await expect(page.getByText('Release blocked', { exact: true })).toBeVisible();
  check('Validation snapshot persists across draft navigation');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'draft-studio-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  check('Draft form, options, evidence and history fit the mobile viewport');
  await page.getByRole('region', { name: 'Advisory draft review', exact: true }).screenshot({ path: path.join(output, 'review-mobile.png') });
  await page.getByRole('region', { name: 'Draft validation', exact: true }).screenshot({ path: path.join(output, 'validation-mobile.png') });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('link', { name: 'Student dashboard', exact: true }).click();
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, cookies: document.cookie }))).toEqual({ local: 0, session: 0, cookies: '' }); check('No token or identity is persisted in browser storage/cookies');
  await page.screenshot({ path: path.join(output, 'workspace-desktop.png'), fullPage: true });
  await page.getByRole('link', { name: 'My account', exact: true }).click(); await expect(page.getByText('review.student@example.com')).toBeVisible();
  await page.getByLabel('Current password', { exact: true }).fill('wrong-password'); await page.getByLabel('New password', { exact: true }).fill('new-fixture-pass-67890'); await page.getByLabel('Confirm new password', { exact: true }).fill('new-fixture-pass-67890');
  await page.getByRole('button', { name: 'Update password' }).click(); await expect(page.getByRole('alert')).toBeVisible(); await expect(page.getByRole('heading', { name: 'My account' })).toBeVisible(); check('Wrong current password is rejected while a valid session remains usable');
  await page.getByLabel('Current password', { exact: true }).fill('fixture-pass-12345'); await page.getByRole('button', { name: 'Update password' }).click(); await expect(page.getByText(/Password updated/)).toBeVisible(); await signIn('new-fixture-pass-67890'); check('Password change revokes sessions and the new password signs in');
  await page.reload(); await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible(); check('Reload requires a fresh login as documented');
  await signIn('new-fixture-pass-67890');
  await expect(page.getByRole('radio', { name: 'Medium', exact: true })).toBeChecked(); check('Student preference persists after a new browser login');
  // A second real session verifies server-side all-session revocation.
  const second = await fetch(`http://127.0.0.1:${apiPort}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'review.student@example.com', password: 'new-fixture-pass-67890' }) });
  expect(second.status).toBe(200); const otherToken = (await second.json()).access_token;
  await page.getByRole('link', { name: 'My account', exact: true }).click(); await page.screenshot({ path: path.join(output, 'account-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Sign out everywhere' }).click(); await page.getByRole('button', { name: 'Confirm sign out' }).click(); await expect(page.getByText('All sessions have been signed out.')).toBeVisible();
  const otherMe = await fetch(`http://127.0.0.1:${apiPort}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${otherToken}` } }); expect(otherMe.status).toBe(401); check('Sign out everywhere revokes a separate real session');
  await page.setViewportSize({ width: 390, height: 844 }); await page.screenshot({ path: path.join(output, 'login-mobile.png'), fullPage: true });
  await signIn('new-fixture-pass-67890'); await page.screenshot({ path: path.join(output, 'workspace-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Toggle navigation' }).click(); await page.getByRole('link', { name: 'My account', exact: true }).click(); await expect(page.getByRole('heading', { name: 'My account' })).toBeVisible();
  await page.screenshot({ path: path.join(output, 'account-mobile.png'), fullPage: true }); check('Mobile navigation and account layout work without horizontal overflow');
  await page.getByRole('button', { name: 'Toggle navigation' }).click(); await page.getByRole('button', { name: 'Sign out', exact: true }).click(); await expect(page.getByText('You have been signed out.')).toBeVisible(); check('Single-session sign-out completes through the real backend');
  await page.setViewportSize({ width: 1440, height: 1000 });
  async function teacherSignIn() {
    await page.getByLabel('Email address').fill('teacher.fixture@example.com'); await page.getByLabel('Password', { exact: true }).fill('Fixture teacher 42!'); await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Welcome, Review.' })).toBeVisible();
  }
  await teacherSignIn(); await expect(page.getByLabel('Your courses: 0', { exact: true })).toBeVisible(); await expect(page.getByText('Your first course starts here')).toBeVisible(); check('Teacher dashboard loads stored counts and an honest empty state');
  await page.getByRole('link', { name: 'Study materials', exact: true }).click();
  await expect(page.getByText('Your library starts here')).toBeVisible();
  check('Teacher cannot see the student private library');
  await page.getByRole('link', { name: 'Generate MCQs', exact: true }).click();
  await expect(page.getByText('Your saved drafts will appear here.', { exact: true })).toBeVisible();
  check('Teacher cannot see the student private drafts');
  await page.getByRole('link', { name: 'Study materials', exact: true }).click();
  await page.getByLabel('Material title', { exact: true }).fill('Teacher source');
  await page.getByLabel('Choose PDF', { exact: true }).setInputFiles({ name: 'teacher.pdf', mimeType: 'application/pdf', buffer: fixturePdf.stdout });
  await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Continue to questions', exact: true })).toBeVisible({ timeout: 45000 });
  await page.getByRole('link', { name: 'Continue to questions', exact: true }).click();
  await page.getByLabel('Draft topic', { exact: true }).fill('transactions');
  await page.getByRole('button', { name: 'Create test draft', exact: true }).click();
  await expect(page.getByText('Test draft — not AI-generated', { exact: true })).toBeVisible();
  await expect(page.locator('.draft-evidence')).toContainText('Transactions preserve consistency');
  check('Teacher generates a separate private test draft with original page evidence');
  await expect(page.getByText('No saved review reports yet.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Run test review', exact: true }).click();
  await expect(page.getByText('Test report · AI quality not evaluated', { exact: true })).toBeVisible();
  check('Teacher creates a separate test review for their own draft');
  await page.getByRole('link', { name: 'Open teacher review', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Version 1', exact: true })).toBeVisible();
  await expect(page.getByText('1 question · latest versions', { exact: true })).toBeVisible();
  await page.getByLabel('Teacher review note', { exact: true }).fill('Inspected this test question');
  await expect(page.getByRole('button', { name: 'Approve this version', exact: true })).toBeDisabled();
  check('Teacher review opens owned source evidence and blocks approval of mock content');
  const originalStem = await page.locator('.teacher-review-detail .draft-stem').innerText();
  await page.getByText('Edit as a new version', { exact: true }).click();
  const editor = page.getByRole('form', { name: 'Edit question version', exact: true });
  await editor.getByLabel('Question', { exact: true }).fill('Which statement describes database transactions?');
  await editor.getByLabel('Reason for this edit', { exact: true }).fill('Clarify wording for classroom review');
  await editor.getByRole('button', { name: 'Save new version', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Version 2', exact: true })).toBeVisible();
  await expect(page.getByText('Version 2 saved. Fresh review and validation are required.', { exact: true })).toBeVisible();
  await expect(page.getByText('No saved review reports yet.', { exact: true })).toBeVisible();
  await expect(page.getByText('No saved validation reports yet.', { exact: true })).toBeVisible();
  check('Editing creates version 2 with no inherited AI review, validation or approval');
  await page.getByRole('button', { name: 'View version 1', exact: true }).click();
  await expect(page.locator('.teacher-review-detail .draft-stem')).toHaveText(originalStem);
  await expect(page.getByText('Edit as a new version', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'View version 2', exact: true }).click();
  await expect(page.locator('.teacher-review-detail .draft-stem')).toHaveText('Which statement describes database transactions?');
  check('Version history preserves original content and keeps superseded versions read-only');
  await page.getByRole('button', { name: 'Run test review', exact: true }).click();
  await expect(page.getByText('Test report · AI quality not evaluated', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Run validation', exact: true }).click();
  await expect(page.getByText('Release blocked', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Refresh approval checks', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Approve this version', exact: true })).toBeDisabled();
  await expect(page.getByRole('article', { name: 'Saved review result', exact: true })).toBeVisible();
  await expect(page.getByText('Release blocked', { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'teacher-review-desktop.png'), fullPage: true });
  check('Fresh checks on an edited mock question still cannot enable approval');
  await page.getByLabel('Teacher review note', { exact: true }).fill('Placeholder options are unsuitable');
  await page.getByRole('button', { name: 'Reject this version', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm rejection', exact: true }).click();
  await expect(page.getByText('Version rejected. Save a corrected version to reconsider it.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reject this version', exact: true })).toBeDisabled();
  check('Explicit rejection persists a teacher note and requires another version');
  await page.getByText('Edit as a new version', { exact: true }).click();
  await editor.getByLabel('Reason for this edit', { exact: true }).fill('Reconsider after correcting the wording');
  await editor.getByRole('button', { name: 'Save new version', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Version 3', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Teacher dashboard', exact: true }).click();
  await page.getByRole('link', { name: 'Teacher review', exact: true }).click();
  await page.getByRole('button', { name: /transactions v3/ }).click();
  await expect(page.getByRole('heading', { name: 'Version 3', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Version history', exact: true })).toContainText('Placeholder options are unsuitable');
  check('Latest version and previous teacher decisions survive navigation');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText('Edit as a new version', { exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'teacher-review-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  check('Teacher editor and version history fit a mobile viewport');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('link', { name: 'Teacher dashboard', exact: true }).click();
  await page.getByRole('button', { name: 'Create course', exact: true }).click(); await page.getByLabel('Course title').fill('Database Management Systems'); await page.getByRole('button', { name: 'Save course', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Database Management Systems', exact: true })).toBeVisible(); await page.getByLabel('Topic name').fill('Relational algebra'); await page.getByRole('button', { name: 'Add topic', exact: true }).click(); await expect(page.getByText('Relational algebra', { exact: true })).toBeVisible(); await expect(page.getByLabel('Your courses: 1', { exact: true })).toBeVisible(); check('Teacher creates a persisted course and topic; counts refresh');
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'teacher-desktop.png'), fullPage: true });

  await page.getByRole('link', { name: 'Assessments', exact: true }).click();
  await page.getByRole('button', { name: 'Create assessment', exact: true }).click();
  await page.getByLabel('Assessment title', { exact: true }).fill('Transactions review');
  await page.getByLabel('Course', { exact: true }).selectOption({ label: 'Database Management Systems' });
  await page.getByRole('checkbox', { name: /Which statement describes database transactions/ }).check();
  await page.getByLabel('Time limit in minutes', { exact: true }).fill('20');
  await page.getByRole('button', { name: 'Save new assessment', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Transactions review', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Publish assessment', exact: true })).toBeDisabled();
  check('Teacher saves an assessment with pinned versions and mock publication stays blocked');
  await page.getByLabel('Student email', { exact: true }).fill('review.student@example.com');
  await page.getByRole('button', { name: 'Allow student', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Remove access for review.student@example.com', exact: true })).toBeVisible();
  check('Teacher adds a registered student to the assessment participant list');
  await page.getByRole('link', { name: 'Teacher dashboard', exact: true }).click();
  await page.getByRole('link', { name: 'Assessments', exact: true }).click();
  await page.getByRole('button', { name: /Transactions review/ }).click();
  await expect(page.getByText('20 min', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Remove access for review.student@example.com', exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(output, 'assessments-desktop.png'), fullPage: true });
  check('Assessment settings and participants persist after navigation');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'assessments-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  check('Assessment publication controls fit a mobile viewport');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('link', { name: 'Teacher dashboard', exact: true }).click();
  await page.getByRole('button', { name: 'Create course', exact: true }).click(); await page.getByLabel('Course title').fill('database management systems'); await page.getByRole('button', { name: 'Save course', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('already have a course'); await page.getByRole('button', { name: 'Cancel', exact: true }).click(); check('Duplicate teacher course is rejected without creating an extra row');
  await page.reload(); await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible(); await teacherSignIn(); await page.getByRole('button', { name: /Database Management Systems/ }).click(); await expect(page.getByText('Relational algebra', { exact: true })).toBeVisible(); check('Saved courses and topics survive a new browser login');
  await page.setViewportSize({ width: 390, height: 844 }); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: path.join(output, 'teacher-mobile.png'), fullPage: true }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true); check('Teacher overview and topic editor fit the mobile viewport');
  await page.getByRole('button', { name: 'Toggle navigation' }).click(); await page.getByRole('button', { name: 'Sign out', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await page.getByLabel('Email address').fill('review.student@example.com'); await page.getByLabel('Password', { exact: true }).fill('new-fixture-pass-67890');

  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome, Review.' })).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Join assessment', exact: true }).click();
  await page.getByLabel('Reference code', { exact: true }).fill('MCQ-0000-0000-0000-0000-0000');
  await page.getByRole('button', { name: 'Join assessment', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('This code cannot grant access');
  await page.screenshot({ path: path.join(output, 'join-assessment-desktop.png'), fullPage: true });
  check('Student code entry rejects an unknown code without disclosing question content');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'join-assessment-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  check('Student code entry fits mobile and never starts an attempt');
  if (process.env.E2E_SCAN_PDF) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('link', { name: 'Study materials', exact: true }).click();
    await page.getByLabel('Material title', { exact: true }).fill('Scanned upload regression');
    await page.getByLabel('Choose PDF', { exact: true }).setInputFiles(process.env.E2E_SCAN_PDF);
    await page.getByRole('button', { name: 'Upload and process', exact: true }).click();
    await expect(page.getByText('PDF saved. Extracted text is ready to review.')).toBeVisible({ timeout: 120000 });
    await expect(page.getByText(/Scanned text recognized on pages 1, 2, 3, 4/)).toBeVisible();
    await expect(page.locator('.source-chunk').first()).toContainText(/prompt engineering/i);
    await page.getByRole('button', { name: 'Next page', exact: true }).click();
    await expect(page.getByText('Page 2 of 4', { exact: true })).toBeVisible();
    await expect(page.locator('.source-chunk').first()).not.toBeEmpty();
    await page.screenshot({ path: path.join(output, 'scanned-pdf-success.png'), fullPage: true });
    check('Reported scanned PDF uploads, OCR text persists with provenance, and page navigation works');
    await page.setViewportSize({ width: 390, height: 844 });
  }
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByLabel('Email address').fill('review.student@example.com'); await page.getByLabel('Password', { exact: true }).fill('new-fixture-pass-67890');
  await page.goto(origin + '/register');
  await page.getByLabel('Account type').selectOption('teacher');
  await page.getByLabel('Full name').fill('New Teacher Fixture');
  await page.getByLabel('Email address').fill('new.teacher@example.com');
  await page.getByLabel('Password', { exact: true }).fill('new-teacher-fixture-123');
  await page.getByLabel('Confirm password', { exact: true }).fill('new-teacher-fixture-123');
  await page.screenshot({ path: path.join(output, 'teacher-signup.png'), fullPage: true });
  await page.getByRole('button', { name: 'Create teacher account', exact: true }).click();
  await expect(page.getByText(/Your teacher account has been created/)).toBeVisible();
  await page.getByRole('button', { name: 'Continue to sign in' }).click();
  await page.getByLabel('Email address').fill('new.teacher@example.com');
  await page.getByLabel('Password', { exact: true }).fill('new-teacher-fixture-123');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome, New.' })).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.getByRole('link', { name: 'Teacher dashboard', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Student dashboard', exact: true })).toHaveCount(0);
  check('Teacher signup and shared login open the correct isolated teacher dashboard');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByLabel('Email address').fill('review.student@example.com');
  await page.getByLabel('Password', { exact: true }).fill('new-fixture-pass-67890');
  api.kill(); await once(api, 'exit'); await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.getByRole('alert')).toBeVisible(); check('Stopped backend produces a recoverable on-screen error');
  expect(errors).toEqual([]); expect(external).toEqual([]); check('No browser runtime errors or external network dependencies');
  expect(policyViolations).toEqual([]);
  check('Normal application use causes no content-security-policy violations');
  console.log(`Completed ${passed} real-browser checks. Synthetic accounts discarded when fixture stops.`);
} catch (error) {
  const failedPage = browser?.contexts()[0]?.pages()[0];
  if (failedPage) {
    await failedPage.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
    console.log(await failedPage.locator('main').ariaSnapshot().catch(() => 'No snapshot'));
  }
  throw error;
} finally {
  await browser?.close();
  for (const child of children.reverse()) {
    if (child.exitCode !== null) continue;
    child.stdin.end('stop\n');
    if (child.spawnargs.some(arg => arg.includes('backend-server.mjs'))) await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 2000))]);
    if (child.exitCode === null) { child.kill(); await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 2000))]); }
  }
}






