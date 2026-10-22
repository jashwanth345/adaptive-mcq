// Test-only, in-memory PostgreSQL adapter. Never used by the application launcher.
import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { PGLiteSocketServer } from '@electric-sql/pglite-socket';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const python = process.env.TEST_PYTHON || 'python';
const mode = process.argv[2] || 'ready';
if (!['ready', 'teacher', 'attempt', 'core', 'empty', 'mismatch', 'unprivileged', 'unsafe'].includes(mode)) throw new Error('Unknown fixture mode');
const db = new PGlite({ extensions: { vector } });
await db.waitReady;
if (mode !== 'empty') {
  const command = [fileURLToPath(new URL('../migrate.py', import.meta.url)), 'render'];
  if (mode === 'core') command.push('--target', '1');
  const result = spawnSync(python, command, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error('Could not render fixture migrations');
  await db.exec(result.stdout);
}
if (mode === 'mismatch') await db.exec("UPDATE mcq_meta.schema_migrations SET checksum='fixture-mismatch' WHERE version='002_vectors'");
await db.exec('CREATE ROLE phase3_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS');
if (mode !== 'empty') {
  await db.exec('GRANT USAGE ON SCHEMA mcq TO phase3_runtime');
  if (mode !== 'unprivileged') await db.exec('GRANT USAGE ON SCHEMA mcq_meta TO phase3_runtime; GRANT SELECT ON mcq_meta.schema_migrations TO phase3_runtime');
  await db.exec('CREATE TABLE mcq.phase3_transaction_fixture(id integer PRIMARY KEY); GRANT SELECT, INSERT ON mcq.phase3_transaction_fixture TO phase3_runtime');
  if (mode !== 'core') {
    const grants = readFileSync(new URL('../auth_runtime_grants.sql', import.meta.url), 'utf8')
      .replace(/^\\set.*$/gm, '').replaceAll(':"runtime_role"', 'phase3_runtime');
    await db.exec(grants);
    const teacherGrants = readFileSync(new URL('../teacher_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime');
    await db.exec(teacherGrants);
    await db.exec(readFileSync(new URL('../generator_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../verifier_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../validation_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../review_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../assessment_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../attempt_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../adaptive_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../feedback_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../analytics_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../evaluation_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../rag_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../material_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    await db.exec(readFileSync(new URL('../student_runtime_grants.sql', import.meta.url), 'utf8').replaceAll(':"runtime_role"', 'phase3_runtime'));
    if (mode === 'unprivileged') await db.exec('REVOKE USAGE ON SCHEMA mcq_meta FROM phase3_runtime');
  }
}
if (mode === 'teacher' || mode === 'attempt') {
  // Synthetic browser-test teacher only, in a disposable database.
  const hashed = spawnSync(python, ['-c', 'from argon2 import PasswordHasher; print(PasswordHasher(memory_cost=19456,time_cost=2,parallelism=1).hash("Fixture teacher 42!"))'], { encoding: 'utf8' });
  if (hashed.status !== 0) throw new Error('Fixture password hashing failed');
  const created = await db.query("INSERT INTO mcq.users(email,display_name,password_hash) VALUES('teacher.fixture@example.com','Review Teacher',$1) RETURNING id", [hashed.stdout.trim()]);
  await db.query("INSERT INTO mcq.user_roles(user_id,role) VALUES($1,'teacher')", [created.rows[0].id]);
  if (mode === 'attempt') { const { seedAttemptFixture } = await import('./attempt-fixture.mjs'); await seedAttemptFixture(db, created.rows[0].id, hashed.stdout.trim()); }
}
// PGlite socket does not provide native password/role authentication. SET ROLE
// explicitly exercises SQL privileges in its single embedded session, not login.
if (mode !== 'unsafe') await db.exec('SET ROLE phase3_runtime');
const server = new PGLiteSocketServer({ db, host: '127.0.0.1', port: 0, maxConnections: 1 });
await server.start();
console.log(JSON.stringify({ connection: server.getServerConn(), mode }));
let closing = false;
async function close() {
  if (closing) return;
  closing = true;
  await server.stop();
  await db.close();
  process.exit(0);
}
process.stdin.resume();
process.stdin.on('data', close);
process.stdin.on('end', close);
process.on('SIGINT', close);
process.on('SIGTERM', close);
