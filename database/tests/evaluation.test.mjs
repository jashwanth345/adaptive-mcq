// Synthetic evaluation storage and privilege checks; no research measurements.
import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const db = new PGlite({ extensions: { vector } }); let count = 0;
async function check(name, fn) { await fn(); count++; console.log('PASS ' + name); }
const one = async (sql, args = []) => (await db.query(sql, args)).rows[0];
try {
 const rendered = spawnSync(process.env.TEST_PYTHON || 'python', [fileURLToPath(new URL('../migrate.py', import.meta.url)), 'render'], { encoding: 'utf8' });
 assert.equal(rendered.status, 0, rendered.stderr); await db.exec(rendered.stdout);
 const teacher = randomUUID(), other = randomUUID(), student = randomUUID();
 for (const id of [teacher, other, student]) { await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,$2,'Synthetic user','fixture-not-a-password')", [id, id + '@example.com']); await db.query('INSERT INTO mcq.user_roles VALUES($1,$2)', [id, id === student ? 'student' : 'teacher']); }
 const access = async (account, op, target = null, retry = null, body = {}) => (await one('SELECT mcq.evaluation_access($1,$2,$3,$4,$5::jsonb) AS r', [account, op, target, retry, JSON.stringify(body)])).r;
 const body = () => ({ run: { id: randomUUID(), format: 'evaluation-run-v1', mode: 'mock', completed: true }, summary: { format: 'evaluation-summary-v1' } });
 const retry = randomUUID(), first = body();
 await check('owned immutable runs are retry-safe and isolated', async () => {
  const saved = await access(teacher, 'save', null, retry, first);
  assert.equal(saved.id, first.run.id); assert.deepEqual(await access(teacher, 'save', null, retry, body()), saved);
  assert.equal((await access(other, 'list')).items.length, 0); assert.equal((await access(other, 'get', saved.id)).error, 'EVALUATION_NOT_FOUND');
  await assert.rejects(db.query('UPDATE mcq.evaluation_runs SET summary=$1 WHERE id=$2', ['{}', saved.id]));
  await assert.rejects(db.query('DELETE FROM mcq.evaluation_runs WHERE id=$1', [saved.id]));
 });
 await check('real-mode and incomplete artifacts are rejected', async () => {
  for (const update of [{ mode: 'local' }, { completed: false }]) { const invalid = body(); Object.assign(invalid.run, update); assert.equal((await access(teacher, 'save', null, randomUUID(), invalid)).error, 'EVALUATION_INVALID'); }
  assert.equal((await access(student, 'list')).error, 'EVALUATION_FORBIDDEN');
 });
 await check('storage and its audit event roll back together', async () => {
  const sample = body(); await db.exec('BEGIN'); await access(teacher, 'save', null, randomUUID(), sample); await db.exec('ROLLBACK');
  assert.equal((await access(teacher, 'get', sample.run.id)).error, 'EVALUATION_NOT_FOUND');
  assert.equal(Number((await one('SELECT count(*) AS n FROM mcq.audit_events WHERE entity_id=$1', [sample.run.id])).n), 0);
 });
 await check('quota limits new runs while existing retries remain readable', async () => {
  for (let n = 1; n < 20; n++) await access(teacher, 'save', null, randomUUID(), body());
  assert.equal((await access(teacher, 'list')).items.length, 20);
  assert.equal((await access(teacher, 'save', null, randomUUID(), body())).error, 'EVALUATION_LIMIT');
  assert.equal((await access(teacher, 'retry', null, retry)).id, first.run.id);
 });
 await check('runtime receives function access only and role revocation closes it', async () => {
  await db.exec('CREATE ROLE evaluation_runtime; GRANT USAGE ON SCHEMA mcq TO evaluation_runtime');
  await db.exec(readFileSync(new URL('../evaluation_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'evaluation_runtime'));
  for (const table of ['evaluation_runs', 'answers', 'questions']) assert.equal((await one("SELECT has_table_privilege('evaluation_runtime',$1,'SELECT,INSERT,UPDATE,DELETE') AS p", ['mcq.' + table])).p, false);
  await db.exec('SET ROLE evaluation_runtime'); assert.equal((await access(teacher, 'list')).items.length, 20); await db.exec('RESET ROLE');
  await db.query("DELETE FROM mcq.user_roles WHERE user_id=$1 AND role='teacher'", [teacher]); assert.equal((await access(teacher, 'list')).error, 'EVALUATION_FORBIDDEN');
 });
 console.log(`${count} evaluation database checks passed. Synthetic evidence only.`);
} finally { await db.close(); }
