// Real-browser checks against the existing backend and a disposable PostgreSQL fixture.
// Synthetic users/database only. E2E_LIGHTWEIGHT=1 skips embedding inference;
// generator always uses the labelled deterministic test fixture.
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { createInterface } from 'node:readline';
import { mkdirSync, existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const frontend = fileURLToPath(new URL('..', import.meta.url));
const root = path.resolve(frontend, '..');
const output = process.env.E2E_OUTPUT || path.join(frontend, 'attempt-test-results');
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
  const pg = start(process.execPath, [path.join(root, 'database/tests/backend-server.mjs'), 'attempt'], { TEST_PYTHON: python });
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
  const page = await context.newPage(); const errors = []; const external = [];
  page.on('pageerror', error => errors.push(error.message)); page.on('request', req => { if (!req.url().startsWith(origin)) external.push(req.url()); });
  await page.goto(origin + '/login');
  await page.getByLabel('Email address').fill('attempt.student@example.com');
  await page.getByLabel('Password', { exact: true }).fill('Fixture teacher 42!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome, Attempt.' })).toBeVisible();
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'My analytics',exact:true}).click();
  await expect(page.getByText('No attempts yet',{exact:true})).toBeVisible(); check('Student analytics starts empty without fabricated metrics');
  await page.getByRole('link', { name: 'Join assessment', exact: true }).first().click();
  await page.getByLabel('Reference code', { exact: true }).fill('MCQ-1234-5678-ABCD-EF01-2345');
  await page.getByRole('button', { name: 'Join assessment', exact: true }).click();
  await page.getByRole('button', { name: 'Start or resume assessment', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Synthetic classroom assessment', exact: true })).toBeVisible();
  check('Authenticated code admission starts the synthetic published snapshot');
  await expect(page.getByText(/Correct answer:/)).toHaveCount(0);
  await page.getByRole('radio', { name: /Normalization/ }).check();
  await page.getByRole('checkbox', { name: 'Flag for review' }).check();
  await page.getByRole('button', { name: 'Save progress', exact: true }).click();
  await expect(page.getByText('Progress saved on this computer.')).toBeVisible();
  await page.getByRole('button', { name: 'Reload saved attempt', exact: true }).click();
  await expect(page.getByRole('radio', { name: /Normalization/ })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: 'Flag for review' })).toBeChecked();
  check('Answer and flag persist through a real server reload; no solution is leaked');
  await page.screenshot({path:path.join(output,'attempt-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(output,'attempt-mobile.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  check('Attempt controls and option text fit mobile');
  await page.setViewportSize({width:1440,height:1000});
  for(let n=1;n<3;n++) { await page.getByRole('button',{name:'Next',exact:true}).click(); await page.getByRole('radio',{name:/Normalization/}).check(); }
  await page.getByRole('button',{name:'Save progress',exact:true}).click();
  await expect(page.getByText('Progress saved on this computer.')).toBeVisible();
  await page.getByRole('button',{name:'Submit assessment',exact:true}).click();
  await page.getByRole('button',{name:'Confirm submission',exact:true}).click();
  await expect(page.getByText('3 / 3',{exact:true})).toBeVisible();
  await expect(page.getByText(/Correct answer:/)).toHaveCount(3);
  await page.getByRole('heading', {name:'Synthetic classroom assessment',exact:true}).focus();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path:path.join(output,'results-desktop.png'),fullPage:true});
  check('Server grades shuffled options and releases three stored solutions after submission');
  await page.getByRole('button',{name:'Reload saved attempt',exact:true}).click();
  await expect(page.getByText('3 / 3',{exact:true})).toBeVisible();
  check('Completed result remains stable on reload');


  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'My analytics',exact:true}).click();
  await expect(page.getByText('3 correct / 3 answered approved items',{exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Attempt history'}).getByRole('cell',{name:'100.0% 3 / 3 points',exact:true})).toBeVisible();
  await page.getByRole('heading',{name:'My analytics',exact:true}).focus();await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(output,'analytics-student-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'analytics-student-mobile.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  check('Released student analytics shows real fixture counts and fits mobile');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('link',{name:'Recommendations & topic mastery',exact:true}).click();
  await expect(page.getByRole('heading',{name:'3 eligible responses',exact:true})).toBeVisible();check('Analytics connects to the existing first-exposure learning profile');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.getByLabel('Email address').fill('teacher.fixture@example.com');await page.getByLabel('Password',{exact:true}).fill('Fixture teacher 42!');await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Evaluation lab',exact:true}).click();
  await expect(page.getByText('No evaluation runs yet. No research results have been assumed.')).toBeVisible();
  await page.getByRole('button',{name:'Run synthetic smoke check',exact:true}).click();
  await expect(page.getByRole('region',{name:'Evaluation conditions'}).getByRole('row')).toHaveCount(5);
  await expect(page.getByRole('cell',{name:'To be evaluated',exact:true})).toHaveCount(4);
  check('Teacher runs isolated synthetic A/B/C/D comparison without AI claims');
  async function artifact(button, filename) {
    const ready=page.waitForEvent('download'); await page.getByRole('button',{name:button,exact:true}).click();
    const file=await ready; const dest=path.join(output,filename); await file.saveAs(dest); return JSON.parse(readFileSync(dest,'utf8'));
  }
  const run=await artifact('Download run evidence','evaluation-run.json');
  expect(run.mode).toBe('mock'); expect(run.records).toHaveLength(16); expect(run.records.every(r=>r.publication_eligible===false)).toBe(true);
  check('Run download contains provenance and sixteen non-publishable fixture slots');
  const pack=await artifact('Download review bundle','operator-review-bundle.json');
  expect(pack.reviewer_items.items).toHaveLength(8); expect(Object.keys(pack.operator_only_map.blind_to_candidate)).toHaveLength(8);
  check('Review export deduplicates candidates and labels the private allocation map');
  await page.getByRole('button',{name:/Open check/}).click(); await expect(page.getByRole('table')).toBeVisible(); check('Saved check reopens from the backend');
  const exportButton=page.getByRole('button',{name:'Download private study events',exact:true});
  await expect(exportButton).toBeDisabled(); await page.getByRole('checkbox',{name:'Synthetic classroom assessment',exact:true}).check(); await expect(exportButton).toBeDisabled();
  await page.getByRole('checkbox',{name:/I confirm permission/}).check();
  const study=await artifact('Download private study events','private-adaptive-events.json');
  expect(study.events).toHaveLength(3); expect(study.events.every(e=>e.learner.startsWith('learner-'))).toBe(true);
  expect(JSON.stringify(study)).not.toContain('attempt.student@example.com');
  check('Consent-confirmed export contains three eligible pseudonymous fixture events');
  await page.getByRole('heading',{name:'Evaluation lab',exact:true}).focus(); await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(output,'evaluation-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844}); await page.screenshot({path:path.join(output,'evaluation-mobile.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true); check('Evaluation lab fits desktop and mobile without page overflow');
  expect(errors).toEqual([]);expect(external).toEqual([]);check('No browser runtime errors or external requests');
  console.log(`Completed ${passed} evaluation browser checks. Synthetic software evidence only.`);
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






