// Disposable synthetic records only; no inference or study results.
import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { randomUUID, createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { seedAttemptFixture } from './attempt-fixture.mjs';
const db = new PGlite({ extensions: { vector } }); let count = 0;
async function check(name, fn) { await fn(); count++; console.log('PASS ' + name); }
const one = async (sql, args = []) => (await db.query(sql, args)).rows[0];
try {
 const rendered = spawnSync(process.env.TEST_PYTHON || 'python', [fileURLToPath(new URL('../migrate.py', import.meta.url)), 'render'], { encoding: 'utf8' });
 assert.equal(rendered.status, 0, rendered.stderr); await db.exec(rendered.stdout);
 const teacher = randomUUID(); await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,'teacher@example.com','Synthetic teacher','synthetic-hash-not-a-login')", [teacher]); await db.query("INSERT INTO mcq.user_roles VALUES($1,'teacher')", [teacher]);
 const f = await seedAttemptFixture(db, teacher, 'synthetic-hash-not-a-login');
 const digest = createHash('sha256').update(f.code.replaceAll('-', '')).digest('hex');
 const analytics = async (account, audience, target = null, ranking = false) => (await one('SELECT mcq.analytics_data($1,$2,$3,0,20,$4) AS r', [account, audience, target, ranking])).r;
 const action = async (account, target, op, body = {}) => (await one('SELECT mcq.attempt_action($1,$2,$3,$4,$5::jsonb) AS r', [account, target, randomUUID(), op, JSON.stringify(body)])).r;
 async function complete(student) {
  await db.query('SELECT mcq.join_assessment($1,$2)', [student, digest]);
  const id = (await action(student, f.aid, 'start')).attempt_id;
  const view = (await one('SELECT mcq.attempt_view($1,$2) AS r', [student, id])).r;
  await action(student, id, 'save', { revision: 1, answers: view.items.map(x => ({ position: x.position, selected_option: x.options.indexOf('Normalization'), flagged: false })) });
  await action(student, id, 'submit', { revision: 2 }); return id;
 }
 await complete(f.student);
 const second = randomUUID(); await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,'second@example.com','Second synthetic learner','synthetic-hash-not-a-login')", [second]); await db.query("INSERT INTO mcq.user_roles VALUES($1,'student')", [second]); await db.query('INSERT INTO mcq.student_profiles(user_id) VALUES($1)', [second]);
 await db.query("SELECT mcq.assessment_action($1,$2,gen_random_uuid(),'participant','{\"email\":\"second@example.com\",\"active\":true}',NULL)", [teacher, f.aid]);
 await complete(second);
 await check('ranking ties share rank and student results remain private', async () => {
  const ranked = await analytics(teacher, 'teacher', f.aid, true);
  assert.equal(ranked.ranking.length, 2); assert.deepEqual(ranked.ranking.map(x => x.rank), [1, 1]);
  const own = await analytics(f.student, 'student'); assert.equal(own.summary.students, 1); assert.equal(own.summary.attempts, 1); assert.equal(own.ranking.length, 0); assert.ok(!JSON.stringify(own).includes('Second synthetic learner'));
 });
 await check('private practice stays out of teacher totals and same-named topics stay separate', async () => {
  const version = (await one('SELECT id FROM mcq.question_versions WHERE owner_id=$1', [f.student])).id;
  const id = (await action(f.student, version, 'practice')).attempt_id; assert.ok(id);
  await action(f.student, id, 'submit', { revision: 1 });
  const student = await analytics(f.student, 'student'); assert.equal(student.summary.attempts, 2);
  assert.equal(student.breakdowns.filter(x => x.dimension === 'topic').length, 2);
  assert.equal(student.summary.average_score, 50); assert.equal(student.summary.accuracy, 100);
  assert.equal((await analytics(teacher, 'teacher')).summary.attempts, 2);
 });
 await check('student SQL cannot request teacher scope, ranking or a target', async () => {
  assert.equal((await analytics(f.student, 'teacher')).error, 'ANALYTICS_FORBIDDEN');
  assert.equal((await analytics(f.student, 'student', f.aid)).error, 'ANALYTICS_INVALID');
  assert.equal((await analytics(f.student, 'student', null, true)).error, 'ANALYTICS_INVALID');
  assert.equal((await analytics(teacher, 'teacher', null, true)).error, 'ANALYTICS_INVALID');
  assert.equal((await analytics(teacher, 'teacher', randomUUID())).error, 'ANALYTICS_NOT_FOUND');
 });
 await check('analytics reads do not create jobs or mutate recorded answers', async () => {
  const before = (await db.query('SELECT * FROM mcq.answers ORDER BY attempt_id,version_id')).rows;
  const jobs = (await one('SELECT count(*) AS n FROM mcq.jobs')).n;
  await analytics(teacher, 'teacher', f.aid, true);
  assert.deepEqual((await db.query('SELECT * FROM mcq.answers ORDER BY attempt_id,version_id')).rows, before);
  assert.equal((await one('SELECT count(*) AS n FROM mcq.jobs')).n, jobs);
 });
 await check('analytics-only grant adds no direct table read or write access', async () => {
  await db.exec('CREATE ROLE analytics_runtime; GRANT USAGE ON SCHEMA mcq TO analytics_runtime');
  await db.exec(readFileSync(new URL('../analytics_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'analytics_runtime'));
  for (const table of ['answers', 'attempts', 'attempt_items', 'feedback', 'question_versions']) assert.equal((await one("SELECT has_table_privilege('analytics_runtime',$1,'SELECT,INSERT,UPDATE,DELETE') AS p", ['mcq.' + table])).p, false);
  await db.exec('SET ROLE analytics_runtime');
  assert.equal((await analytics(f.student, 'student')).summary.attempts, 2);
  await db.exec('RESET ROLE');
 });
 await check('revoking the teacher role closes direct SQL analytics access', async () => {
  await db.query("DELETE FROM mcq.user_roles WHERE user_id=$1 AND role='teacher'", [teacher]);
  assert.equal((await analytics(teacher, 'teacher', f.aid)).error, 'ANALYTICS_FORBIDDEN');
 });
 console.log(`${count} analytics database checks passed. Synthetic workflow evidence only.`);
} finally { await db.close(); }

