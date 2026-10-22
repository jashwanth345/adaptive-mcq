// Real-browser checks against the existing backend and a disposable PostgreSQL fixture.
// Synthetic users/database only. E2E_LIGHTWEIGHT=1 skips embedding inference;
// generator always uses the labelled deterministic test fixture.
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { createInterface } from 'node:readline';
import { mkdirSync, existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const frontend = fileURLToPath(new URL('..', import.meta.url));
const root = path.resolve(frontend, '..');
const output = process.env.E2E_OUTPUT || path.join(frontend, 'integration-test-results');
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
  const native = process.env.MCQ_NATIVE_TEST_DATABASE;
  if (native && !/^mcq_acceptance_[a-f0-9]+$/.test(native)) throw new Error('Native journey requires a synthetic acceptance database');
  let dbPort = process.env.DATABASE_PORT;
  if (!native) {
  const pg = start(process.execPath, [path.join(root, 'database/tests/backend-server.mjs'), 'attempt'], { TEST_PYTHON: python });
  const lines = createInterface({ input: pg.stdout });
  const [line] = await Promise.race([once(lines, 'line'), new Promise((_, reject) => { const timer = setTimeout(() => reject(new Error('PostgreSQL fixture startup timed out')), 45000); timer.unref(); })]);
  lines.close(); dbPort = new URL('postgres://' + JSON.parse(line).connection).port;
  }
  const apiPort = await port(); const webPort = await port(); const origin = `http://localhost:${webPort}`;
  const apiEnv = {
    APP_ENV: 'test', API_HOST: '127.0.0.1', API_PORT: String(apiPort), FRONTEND_ORIGIN: origin,
    DATABASE_HOST: '127.0.0.1', DATABASE_PORT: dbPort, DATABASE_NAME: native || 'postgres', DATABASE_USER: native ? 'adaptive_mcq_app' : 'postgres',
    DATABASE_PASSWORD: native ? process.env.DATABASE_PASSWORD : 'fixture-only-password', JWT_SECRET: 'fixture-only-secret-not-for-real-use-12345', DATABASE_POOL_SIZE: native ? '2' : '1',
    AUTH_LOGIN_ACCOUNT_LIMIT: '10', AUTH_LOGIN_IP_LIMIT: '100',
    GENERATOR_MODE: 'mock',
    VERIFIER_MODE: 'mock', HF_HUB_OFFLINE: '1', TRANSFORMERS_OFFLINE: '1',
  };
  const launchApi = () => start(python, ['-m', 'backend.tests.browser_app', '--stdin-shutdown'], apiEnv);
  let api = launchApi();
  await waitReady(`http://127.0.0.1:${apiPort}/api/v1/health/ready`, api);
  const web = start(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), 'preview', frontend, '--host', 'localhost', '--port', String(webPort), '--strictPort'], { LOCAL_API_ORIGIN: `http://127.0.0.1:${apiPort}` });
  await waitReady(origin, web);
  const executable = process.env.E2E_BROWSER || ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
  browser = await chromium.launch({ headless: true, ...(executable ? { executablePath: executable } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage(); const errors = []; const external = [];
  page.on('pageerror', error => errors.push(error.message)); page.on('request', req => { if (!req.url().startsWith(origin)) external.push(req.url()); });
  // Deny external browser traffic; fixtures never run local or cloud models.
  const localOnly = route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort('blockedbyclient');
  await context.route('**/*', localOnly);
  const studentContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await studentContext.route('**/*', localOnly);
  const student = await studentContext.newPage();
  student.on('pageerror', error => errors.push(error.message));
  student.on('request', req => { if (!req.url().startsWith(origin)) external.push(req.url()); });
  async function signIn(target, email) {
    await target.goto(origin + '/login');
    await target.getByLabel('Email address').fill(email);
    await target.getByLabel('Password', { exact: true }).fill('Fixture teacher 42!');
    await target.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(target.getByRole('heading', { name: /Welcome,/ })).toBeVisible();
  }
  const nav = (target, name) => target.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true }).click();
  async function capture(target, name) {
    if (name === 'teacher-dashboard') await expect(target.getByRole('button', { name: 'Refresh overview', exact: true })).toBeEnabled();
    if (name === 'student-dashboard') await expect(target.getByRole('button', { name: 'Refresh dashboard', exact: true })).toBeEnabled();
    await expect(target.getByText(/^Loading/)).toHaveCount(0);
    await expect(target.getByRole('alert')).toHaveCount(0);
    await target.evaluate(() => document.fonts.ready);
    await target.getByRole('heading', { level: 1 }).focus();
    await target.evaluate(() => window.scrollTo(0, 0));
    await target.screenshot({ path: path.join(output, name + '-desktop.png'), fullPage: true });
    await target.setViewportSize({ width: 390, height: 844 });
    expect(await target.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await target.screenshot({ path: path.join(output, name + '-mobile.png'), fullPage: true });
    await target.setViewportSize({ width: 1440, height: 1000 });
  }
  async function studyExport() {
    const ready = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download private study events', exact: true }).click();
    const download = await ready;
    const destination = path.join(output, `private-study-${Date.now()}.json`);
    await download.saveAs(destination);
    return JSON.parse(readFileSync(destination, 'utf8'));
  }
  await signIn(page, 'teacher.fixture@example.com');
  await nav(page, 'Assessments');
  await page.getByRole('button', { name: 'Create assessment', exact: true }).click();
  await page.getByLabel('Assessment title', { exact: true }).fill('DBMS classroom integration — synthetic test');
  await expect(page.getByRole('button', { name: 'Save new assessment', exact: true })).toBeDisabled();
  await page.getByText('Create a course here', { exact: true }).click();
  await page.getByLabel('New course title', { exact: true }).fill('Inline course — synthetic test');
  await page.getByRole('button', { name: 'Create and select course', exact: true }).click();
  await expect(page.getByLabel('Course', { exact: true }).locator('option:checked')).toHaveText('Inline course — synthetic test');
  await expect(page.getByLabel('Assessment title', { exact: true })).toHaveValue('DBMS classroom integration — synthetic test');
  await page.getByLabel('Course', { exact: true }).selectOption({ label: 'Synthetic DBMS course' });
  for (let n = 1; n <= 3; n++) await page.getByRole('checkbox', { name: new RegExp(`Synthetic question ${n}:`) }).check();
  await page.getByLabel('Maximum attempts', { exact: true }).fill('2');
  await page.getByLabel('Randomize question order', { exact: true }).check();
  await page.getByLabel('Randomize option order', { exact: true }).check();
  await page.getByRole('button', { name: 'Save new assessment', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'DBMS classroom integration — synthetic test', exact: true })).toBeVisible();
  await page.getByLabel('Student email', { exact: true }).fill('attempt.student@example.com');
  await page.getByRole('button', { name: 'Allow student', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Remove access for attempt.student@example.com', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Publish assessment', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm publish', exact: true }).click();
  await expect(page.getByText('Assessment published. Share the reference code with permitted students.', { exact: true })).toBeVisible();
  const oldCode = await page.locator('.reference-code strong').innerText();
  expect(oldCode).toMatch(/^MCQ-(?:[A-Z0-9]{4}-){4}[A-Z0-9]{4}$/);
  check('Teacher creates and publishes exact synthetic approved versions through the browser and API');
  await page.getByRole('button', { name: 'Create replacement code', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm replacement', exact: true }).click();
  await expect(page.getByText('New code created. Earlier codes no longer grant access.', { exact: true })).toBeVisible();
  const code = await page.locator('.reference-code strong').innerText();
  expect(code).not.toBe(oldCode);
  await nav(page, 'Teacher dashboard');
  await capture(page, 'teacher-dashboard');
  check('Teacher dashboard displays stored classroom records on desktop and mobile');

  await signIn(student, 'attempt.student@example.com');
  await nav(student, 'Join assessment');
  await student.getByLabel('Reference code', { exact: true }).fill(oldCode);
  await student.getByRole('button', { name: 'Join assessment', exact: true }).click();
  await expect(student.getByRole('alert')).toContainText('This code cannot grant access');
  await student.getByLabel('Reference code', { exact: true }).fill(code);
  await student.getByRole('button', { name: 'Join assessment', exact: true }).click();
  await student.getByRole('button', { name: 'Start or resume assessment', exact: true }).click();
  await expect(student.getByRole('heading', { name: 'DBMS classroom integration — synthetic test', exact: true })).toBeVisible();
  await expect(student.getByText(/Correct answer:/)).toHaveCount(0);
  check('Old reference code is rejected; replacement admits only the permitted student without revealing keys');
  await expect(student).toHaveURL(/\/attempts\/[0-9a-f-]+$/);
  const attemptUrl = student.url();
  await student.getByRole('radio', { name: /Normalization/ }).check();
  await student.getByRole('checkbox', { name: 'Flag for review' }).check();
  let lostSave, committedSave, saveCalls = 0;
  const savePath = '**/api/v1/student/attempts/*/save';
  await student.route(savePath, async route => {
    saveCalls++;
    if (saveCalls === 1) {
      lostSave = route.request().postDataJSON();
      const response = await route.fetch(); expect(response.status()).toBe(200); committedSave = await response.json();
      await route.abort('failed');
    } else { expect(route.request().postDataJSON()).toEqual(lostSave); await route.continue(); }
  });
  await student.getByRole('button', { name: 'Save progress', exact: true }).click();
  await expect(student.getByRole('alert')).toBeVisible();
  await expect(student.getByRole('radio', { name: /Normalization/ })).toBeChecked();
  await student.getByRole('button', { name: 'Save progress', exact: true }).click();
  await expect(student.getByText('Progress saved on this computer.', { exact: true })).toBeVisible();
  expect(saveCalls).toBe(2); expect(committedSave.revision).toBe(2);
  await student.unroute(savePath);
  await student.getByRole('button', { name: 'Reload saved attempt', exact: true }).click();
  await expect(student.getByRole('radio', { name: /Normalization/ })).toBeChecked();
  check('Lost committed-save response retries the same command and preserves the selected answer');

  const oldApiExit = once(api, 'exit'); api.stdin.write('stop\n');
  await Promise.race([oldApiExit, new Promise((_, reject) => { const timer = setTimeout(() => reject(new Error('Graceful test API shutdown timed out')), 15000); timer.unref(); })]);
  await student.getByRole('button', { name: 'Reload saved attempt', exact: true }).click();
  await expect(student.getByRole('alert')).toBeVisible();
  await expect(student.getByText('Saved attempt loaded.', { exact: true })).toHaveCount(0);
  await expect(student.getByText('Progress saved on this computer.', { exact: true })).toHaveCount(0);
  api = launchApi(); await waitReady(`http://127.0.0.1:${apiPort}/api/v1/health/ready`, api);
  const restoredReady = student.waitForResponse(response => response.url().includes('/student/attempts/') && response.request().method() === 'GET' && response.status() === 200);
  await student.getByRole('button', { name: 'Reload saved attempt', exact: true }).click();
  const restored = await (await restoredReady).json();
  expect(restored.revision).toBe(2); expect(restored.items).toEqual(committedSave.items);
  await expect(student.getByRole('checkbox', { name: 'Flag for review' })).toBeChecked();
  check('Backend restart preserves the database session, pinned order, answer, flag and revision');
  await capture(student, 'assessment-player');
  for (let n = 1; n < 3; n++) { await student.getByRole('button', { name: 'Next', exact: true }).click(); await student.getByRole('radio', { name: /Normalization/ }).check(); }
  await student.getByRole('button', { name: 'Save progress', exact: true }).click();
  await expect(student.getByText('Progress saved on this computer.', { exact: true })).toBeVisible();
  let lostSubmit, submitted, submitCalls = 0;
  const submitPath = '**/api/v1/student/attempts/*/submit';
  await student.route(submitPath, async route => {
    submitCalls++;
    if (submitCalls === 1) {
      lostSubmit = route.request().postDataJSON(); const response = await route.fetch(); expect(response.status()).toBe(200); submitted = await response.json(); await route.abort('failed');
    } else { expect(route.request().postDataJSON()).toEqual(lostSubmit); await route.continue(); }
  });
  await student.getByRole('button', { name: 'Submit assessment', exact: true }).click();
  await student.getByRole('button', { name: 'Confirm submission', exact: true }).click();
  await expect(student.getByRole('alert')).toBeVisible();
  await student.getByRole('button', { name: 'Confirm submission', exact: true }).click();
  await expect(student.getByText('3 / 3', { exact: true })).toBeVisible();
  await student.unroute(submitPath);
  expect(submitCalls).toBe(2); expect(submitted.state).toBe('submitted');
  check('Lost submission response retries safely and returns the original server-graded result');
  await capture(student, 'assessment-results');
  await nav(student, 'Student dashboard');
  await capture(student, 'student-dashboard');
  await nav(student, 'My analytics');
  await expect(student.getByText('3 correct / 3 answered approved items', { exact: true })).toBeVisible();
  await expect(student.getByRole('region', { name: 'Attempt history' }).getByRole('row')).toHaveCount(2);
  check('Submission retries create one recorded attempt and three eligible answers in analytics');
  await student.route('**/api/v1/student/analytics?*', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'DATABASE_UNAVAILABLE', message: 'Synthetic outage' } }) }));
  await student.getByRole('button', { name: 'Refresh analytics', exact: true }).click();
  await expect(student.getByRole('alert')).toBeVisible();
  await expect(student.getByText('3 correct / 3 answered approved items', { exact: true })).toHaveCount(0);
  await student.unroute('**/api/v1/student/analytics?*');
  await student.getByRole('button', { name: 'Refresh analytics', exact: true }).click();
  await expect(student.getByText('3 correct / 3 answered approved items', { exact: true })).toBeVisible();
  check('Failed analytics refresh clears stale results and recovers without inventing successful data');

  await nav(page, 'Evaluation lab');
  await page.getByRole('checkbox', { name: 'DBMS classroom integration — synthetic test', exact: true }).check();
  await page.getByRole('checkbox', { name: /I confirm permission/ }).check();
  expect((await studyExport()).events).toHaveLength(3);
  check('Teacher study export agrees with released first-exposure evidence before quarantine');
  await student.getByRole('region', { name: 'Attempt history' }).getByRole('link', { name: 'DBMS classroom integration — synthetic test', exact: true }).click();
  await expect(student).toHaveURL(attemptUrl);
  await student.getByText('Report or rate question 1', { exact: true }).click();
  await student.getByLabel('Feedback comment for question 1', { exact: true }).fill('Synthetic integration report for cross-module quarantine testing.');
  await student.getByRole('form', { name: 'Feedback for question 1', exact: true }).getByRole('button', { name: 'Send feedback', exact: true }).click();
  await expect(student.getByText('Feedback saved. A report does not change your score or automatically confirm an error.', { exact: true })).toBeVisible();
  await nav(page, 'Feedback review');
  await page.getByRole('article').filter({ hasText: '1 unresolved reporters' }).getByRole('link', { name: 'Review reports', exact: true }).click();
  await page.getByLabel('Review action', { exact: true }).selectOption('confirm_defect');
  await page.getByLabel('Decision and follow-up note', { exact: true }).fill('Synthetic confirmed defect for integration testing. Original score must be retained.');
  await expect(page.getByRole('button', { name: 'Save review decision', exact: true })).toBeDisabled();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Save review decision', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Score review: pending', exact: true })).toBeVisible();
  await student.getByRole('button', { name: 'Reload saved attempt', exact: true }).click();
  await expect(student.getByText('3 / 3', { exact: true })).toBeVisible();
  await expect(student.getByText('Solution withheld while this item is under review.', { exact: true })).toBeVisible();
  await expect(student.getByText(/Correct answer:/)).toHaveCount(2);
  check('Confirmed defect withholds one solution while preserving the original score');
  await student.getByRole('link', { name: 'View topic progress and next practice', exact: true }).click();
  await expect(student.getByRole('heading', { name: '2 eligible responses', exact: true })).toBeVisible();
  await nav(student, 'My analytics');
  await expect(student.getByText('2 correct / 2 answered approved items', { exact: true })).toBeVisible();
  await nav(page, 'Evaluation lab');
  await page.getByRole('checkbox', { name: 'DBMS classroom integration — synthetic test', exact: true }).check();
  await page.getByRole('checkbox', { name: /I confirm permission/ }).check();
  const afterQuarantine = await studyExport(); expect(afterQuarantine.events).toHaveLength(2);
  expect(JSON.stringify(afterQuarantine)).not.toContain('attempt.student@example.com');
  check('Quarantine consistently removes one item from mastery, analytics and pseudonymous study export');
  await nav(page, 'Assessments');
  await page.getByRole('button', { name: /DBMS classroom integration — synthetic test/ }).click();
  await page.getByRole('button', { name: 'Close assessment', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm close', exact: true }).click();
  await nav(student, 'Join assessment');
  await student.getByRole('button', { name: 'Refresh joined assessments', exact: true }).click();
  await expect(student.getByRole('button', { name: 'Start or resume assessment', exact: true })).toHaveCount(0);
  await student.getByLabel('Reference code', { exact: true }).fill(code);
  await student.getByRole('button', { name: 'Join assessment', exact: true }).click();
  await expect(student.getByRole('alert')).toContainText('This code cannot grant access');
  check('Closing the assessment blocks new starts and rejoining with the issued code');
  await student.goto(origin + '/evaluation');
  await expect(student.getByRole('heading', { name: 'Welcome back', exact: true })).toBeVisible();
  await signIn(student, 'attempt.student@example.com');
  await student.evaluate(() => { history.pushState({}, '', '/evaluation'); window.dispatchEvent(new PopStateEvent('popstate')); });
  await expect(student.getByRole('heading', { name: 'Teacher access required', exact: true })).toBeVisible();
  check('Reload requires sign-in and a student still cannot open the teacher evaluation route');
  expect(errors).toEqual([]); expect(external).toEqual([]);
  check('No browser runtime errors or external requests across both user contexts');
  console.log(`Completed ${passed} classroom integration checks (${native ? 'native PostgreSQL' : 'embedded PostgreSQL'}). All approval evidence and scores are synthetic fixtures, not AI or learner-study results.`);
} catch (error) {
  const failedPages = browser?.contexts().flatMap(c => c.pages()) ?? [];
  for (let n = 0; n < failedPages.length; n++) {
    await failedPages[n].screenshot({ path: path.join(output, `failure-${n}.png`), fullPage: true }).catch(() => {});
    console.log(await failedPages[n].locator('main').ariaSnapshot().catch(() => 'No snapshot'));
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
