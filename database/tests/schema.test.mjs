import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const runner = fileURLToPath(new URL('../migrate.py', import.meta.url));
const python = process.env.TEST_PYTHON || 'python';
// Preserve the legacy lifecycle fixtures, then explicitly test their upgrade.
function render(target = 4) {
  const args = [runner, 'render', ...(target ? ['--target', String(target)] : [])];
  const result = spawnSync(python, args, { encoding: 'utf8' });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}
let passed = 0;
async function test(name, fn) {
  await fn(); passed++; console.log(`PASS ${name}`);
}
const db = new PGlite({ extensions: { vector } });
const exec = sql => db.exec(sql);
const scalar = async sql => Object.values((await db.query(sql)).rows[0])[0];
async function rejects(sql, code = '23514') {
  let failure;
  try { await exec(sql); } catch (error) { failure = error; }
  try { await exec('ROLLBACK'); } catch {}
  assert.ok(failure, 'Expected database rejection');
  assert.equal(failure.code, code, failure.message);
}
const id = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const u = id(1), student = id(2), stranger = id(3), course = id(4), topic = id(5);
const mat = id(6), doc = id(7), chunk = id(8), question = id(9), ver = id(10), check = id(11);
const assessment = id(12), attempt = id(13), practice = id(14), model = id(15);
const newVersion = (n, extra = '') => `
BEGIN;
INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type)
VALUES('${id(n)}','${question}','${u}',${n},'${topic}','Fixture question ${n}','Fixture explanation',0,'easy','understand','conceptual');
INSERT INTO mcq.options(version_id,ordinal,content) SELECT '${id(n)}',i,'Option '||i FROM generate_series(0,3) i;
${extra}
COMMIT;`;

try {
  await test('fresh core + vector migrations commit', async () => {
    await exec(render());
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'), 4);
    console.log('ENGINE', await scalar('SELECT version()'));
    console.log('VECTOR', await scalar("SELECT extversion FROM pg_extension WHERE extname='vector'"));
  });
  await test('migration replay preserves existing history', async () => {
    const before = await scalar('SELECT max(applied_at)::text FROM mcq_meta.schema_migrations');
    await exec(render());
    assert.equal(await scalar('SELECT max(applied_at)::text FROM mcq_meta.schema_migrations'), before);
  });
  await test('populated version 2 upgrades without changing existing accounts', async () => {
    const upgrade = new PGlite({ extensions: { vector } });
    try {
      await upgrade.exec(render(2));
      await upgrade.exec("INSERT INTO mcq.users(email,display_name,password_hash) VALUES('existing@example.invalid','Existing fixture','fixture-only-not-a-real-password-hash')");
      const before = (await upgrade.query('SELECT id,email,display_name,password_hash FROM mcq.users')).rows;
      await upgrade.exec(render());
      assert.deepEqual((await upgrade.query('SELECT id,email,display_name,password_hash FROM mcq.users')).rows, before);
      assert.equal((await upgrade.query('SELECT count(*)::int AS n FROM mcq_meta.schema_migrations')).rows[0].n,4);
      assert.equal((await upgrade.query('SELECT count(*)::int AS n FROM mcq.auth_sessions')).rows[0].n,0);
    } finally { await upgrade.close(); }
  });
  await test('changed checksum is rejected atomically', async () => {
    const checksum = await scalar("SELECT checksum FROM mcq_meta.schema_migrations WHERE version='002_vectors'");
    await exec("UPDATE mcq_meta.schema_migrations SET checksum='tampered' WHERE version='002_vectors'");
    await rejects(render(), 'P0001');
    await db.query("UPDATE mcq_meta.schema_migrations SET checksum=$1 WHERE version='002_vectors'", [checksum]);
    await exec(render());
  });
  await test('older target cannot act as a downgrade', async () => { await rejects(render(1), 'P0001'); });
  await exec('SET search_path = mcq, public');
  await test('valid teacher/student/course/material fixture', async () => {
    await exec(`
      INSERT INTO users(id,email,display_name,password_hash) VALUES
      ('${u}','teacher@example.invalid','Teacher fixture','not-a-real-login-hash-do-not-use'),
      ('${student}','student@example.invalid','Student fixture','not-a-real-login-hash-do-not-use'),
      ('${stranger}','stranger@example.invalid','Other fixture','not-a-real-login-hash-do-not-use');
      INSERT INTO user_roles VALUES ('${u}','teacher'),('${student}','student'),('${stranger}','student');
      INSERT INTO courses(id,owner_id,title) VALUES('${course}','${u}','Fixture course');
      INSERT INTO course_memberships(course_id,student_id) VALUES('${course}','${student}');
      INSERT INTO topics(id,owner_id,course_id,name) VALUES('${topic}','${u}','${course}','Fixture topic');
      INSERT INTO materials(id,owner_id,title) VALUES('${mat}','${u}','Fixture material');
      INSERT INTO documents(id,material_id,owner_id,version,storage_key,sha256,byte_size,page_count)
        VALUES('${doc}','${mat}','${u}',1,'fixture.pdf',repeat('a',64),100,1);
      INSERT INTO chunks(id,document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version)
        VALUES('${chunk}','${doc}','${u}',0,1,1,'Fixture source',repeat('b',64),3,'fixture-v1');
      INSERT INTO questions(id,owner_id) VALUES('${question}','${u}');
    `);
    await exec(newVersion(10));
  });
  await test('cross-owner document link rejected', () => rejects(`INSERT INTO documents(material_id,owner_id,version,storage_key,sha256,byte_size,page_count)
    VALUES('${mat}','${stranger}',2,'wrong.pdf',repeat('a',64),100,1)`, '23503'));
  await test('path traversal storage key rejected', () => rejects(`INSERT INTO documents(material_id,owner_id,version,storage_key,sha256,byte_size,page_count)
    VALUES('${mat}','${u}',2,'../wrong.pdf',repeat('a',64),100,1)`));
  await test('exactly four options required at commit', () => rejects(`BEGIN;
    INSERT INTO question_versions(question_id,owner_id,version,topic_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type)
    VALUES('${question}','${u}',99,'${topic}','Bad','Missing options',0,'easy','remember','conceptual'); COMMIT;`));
  await test('question content cannot change after insertion', () => rejects(`UPDATE question_versions SET stem='Changed' WHERE id='${ver}'`));
  await test('options cannot be rewritten', () => rejects(`UPDATE options SET content='Changed' WHERE version_id='${ver}'`));
  await test('incomplete model PASS rejected', () => rejects(`INSERT INTO question_verifications(version_id,verifier_model,model_digest,prompt_version,policy_version,status,math_result)
    VALUES('${ver}','fixture','fixture','fixture','fixture','PASS','unsupported')`));
  await test('source, verification and approval can be recorded', async () => {
    await exec(`INSERT INTO question_sources VALUES('${ver}','${chunk}','${u}','Fixture source');
      INSERT INTO question_verifications(id,version_id,verifier_model,model_digest,prompt_version,policy_version,status,
      confidence_score,correctness_score,clarity_score,difficulty_score,distractor_score,grounding_score,duplicate_score,
      blind_option,schema_pass,source_pass,duplicate_pass,math_result,review_required)
      VALUES('${check}','${ver}','fixture-only','fixture-only','test','test','PASS',80,80,80,80,80,80,0,0,true,true,true,'not_applicable',false);
      INSERT INTO question_releases(version_id,verification_id,reviewed_by,state) VALUES('${ver}','${check}','${u}','approved');`);
  });
  await test('reviewer cannot be a different owner', () => rejects(`UPDATE question_releases SET reviewed_by='${stranger}' WHERE version_id='${ver}'`));
  await test('source evidence sealed after verification', () => rejects(`INSERT INTO question_sources VALUES('${ver}','${chunk}','${u}','New evidence')`));
  await test('new edit version has no inherited approval', async () => {
    await exec(newVersion(20));
    assert.equal(await scalar(`SELECT count(*)::int FROM question_releases WHERE version_id='${id(20)}'`), 0);
    await rejects(`INSERT INTO question_releases(version_id,verification_id,reviewed_by,state) VALUES('${id(20)}','${check}','${u}','approved')`);
  });
  await test('advisory test reports save without release-gate evidence', async () => {
    await exec(newVersion(900));
    await exec(`INSERT INTO jobs(id,owner_id,kind,state,idempotency_key) VALUES('${id(901)}','${u}','verify','completed',gen_random_uuid());
      INSERT INTO verifier_reports(id,owner_id,version_id,job_id,mode,recommendation,result)
      VALUES('${id(902)}','${u}','${id(900)}','${id(901)}','mock','NOT_EVALUATED','{"ai_executed":false}');`);
    assert.equal(await scalar(`SELECT count(*)::int FROM question_verifications WHERE version_id='${id(900)}'`),0);
    assert.equal(await scalar(`SELECT count(*)::int FROM question_releases WHERE version_id='${id(900)}'`),0);
  });
  const reportSQL = ({ owner=u, version=id(900), kind='verify', state='completed', mode='mock', recommendation='NOT_EVALUATED', result='{"ai_executed":false}', eligible=false } = {}) => `BEGIN;
    INSERT INTO jobs(id,owner_id,kind,state,idempotency_key) VALUES('${id(903)}','${owner}','${kind}','${state}',gen_random_uuid());
    INSERT INTO verifier_reports(owner_id,version_id,job_id,mode,recommendation,result,publication_eligible)
    VALUES('${owner}','${version}','${id(903)}','${mode}','${recommendation}','${result}',${eligible}); COMMIT;`;
  await test('test report cannot claim AI execution or PASS', async () => {
    await rejects(reportSQL({result:'{"ai_executed":true}'}));
    await rejects(reportSQL({recommendation:'PASS'}));
    await rejects(reportSQL({result:'{}'}));
  });
  await test('advisory report cannot grant publication', () => rejects(reportSQL({eligible:true})));
  await test('report requires a completed verify job', async () => {
    await rejects(reportSQL({kind:'generate'}));
    await rejects(reportSQL({state:'queued'}));
  });
  await test('report owner must own the draft', () => rejects(reportSQL({owner:stranger}), '23503'));
  await test('non-AI draft cannot receive an AI report', () => rejects(reportSQL({mode:'ollama', recommendation:'REJECT'})));
  await test('released draft cannot receive an advisory report', () => rejects(reportSQL({version:ver})));
  await test('saved report cannot be edited or deleted', async () => {
    await rejects(`UPDATE verifier_reports SET result='{}' WHERE id='${id(902)}'`);
    await rejects(`DELETE FROM verifier_reports WHERE id='${id(902)}'`);
  });
  await test('cannot publish empty fixed assessment', async () => {
    await exec(`INSERT INTO assessments(id,owner_id,course_id,title,kind,mode) VALUES('${assessment}','${u}','${course}','Fixture test','classroom','fixed')`);
    await rejects(`UPDATE assessments SET state='published',published_at=now() WHERE id='${assessment}'`);
  });
  await test('unreviewed item prevents publication', async () => {
    await exec(`INSERT INTO assessment_questions VALUES('${assessment}','${u}',1,'${id(20)}',1)`);
    await rejects(`UPDATE assessments SET state='published',published_at=now() WHERE id='${assessment}'`);
    await exec(`DELETE FROM assessment_questions WHERE assessment_id='${assessment}'`);
  });
  await test('reviewed classroom assessment publishes', async () => {
    await exec(`INSERT INTO assessment_questions VALUES('${assessment}','${u}',1,'${ver}',2);
      UPDATE assessments SET state='published',published_at=now() WHERE id='${assessment}';
      INSERT INTO reference_codes(assessment_id,code_digest) VALUES('${assessment}',repeat('c',64))`);
  });
  await test('published question list frozen', () => rejects(`DELETE FROM assessment_questions WHERE assessment_id='${assessment}'`));
  await test('published settings frozen', () => rejects(`UPDATE assessments SET max_attempts=9 WHERE id='${assessment}'`));
  await test('code cannot be repointed', () => rejects(`UPDATE reference_codes SET code_digest=repeat('d',64)`));
  await test('non-member cannot begin classroom attempt', () => rejects(`INSERT INTO attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key)
      VALUES('${assessment}','${u}','${stranger}',1,gen_random_uuid())`));
  await test('member attempt starts and pins item', async () => {
    await exec(`INSERT INTO attempts(id,assessment_id,owner_id,student_id,attempt_number,idempotency_key)
      VALUES('${attempt}','${assessment}','${u}','${student}',1,gen_random_uuid());
      INSERT INTO attempt_items(attempt_id,assessment_id,owner_id,position,version_id,points)
      VALUES('${attempt}','${assessment}','${u}',1,'${ver}',2)`);
  });
  await test('attempt limit enforced', () => rejects(`INSERT INTO attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key)
      VALUES('${assessment}','${u}','${student}',2,gen_random_uuid())`));
  await test('fixed test cannot inject another question', () => rejects(`INSERT INTO attempt_items(attempt_id,assessment_id,owner_id,position,version_id,points)
      VALUES('${attempt}','${assessment}','${u}',2,'${id(20)}',1)`));
  await test('cannot submit unscored attempt', () => rejects(`UPDATE attempts SET state='submitted',submitted_at=now() WHERE id='${attempt}'`));
  await test('answer must reference a presented item', () => rejects(`INSERT INTO answers(attempt_id,version_id,selected_option) VALUES('${attempt}','${id(20)}',0)`, '23503'));
  await test('selected option must exist', () => rejects(`INSERT INTO answers(attempt_id,version_id,selected_option) VALUES('${attempt}','${ver}',9)`, '23503'));
  await test('incorrect answer cannot receive full marks', () => rejects(`INSERT INTO answers(attempt_id,version_id,selected_option,is_correct,awarded_points) VALUES('${attempt}','${ver}',1,true,2)`));
  await test('valid answer, score and atomic submission', async () => {
    await exec(`BEGIN;
      INSERT INTO answers(attempt_id,version_id,selected_option,is_correct,awarded_points,response_ms) VALUES('${attempt}','${ver}',0,true,2,1500);
      UPDATE attempts SET state='submitted',submitted_at=now() WHERE id='${attempt}'; COMMIT;`);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)), 2);
  });
  await test('submitted answer cannot be changed', () => rejects(`UPDATE answers SET selected_option=1 WHERE attempt_id='${attempt}'`));
  await test('second submission rejected', () => rejects(`UPDATE attempts SET submitted_at=now() WHERE id='${attempt}'`));
  await test('feedback tied to actual student', () => rejects(`INSERT INTO feedback(attempt_id,version_id,student_id,category) VALUES('${attempt}','${ver}','${stranger}','ambiguous')`, '23503'));
  await test('feedback recorded and duplicate category rejected', async () => {
    const sql = `INSERT INTO feedback(attempt_id,version_id,student_id,category) VALUES('${attempt}','${ver}','${student}','ambiguous')`;
    await exec(sql); await rejects(sql, '23505');
  });
  await test('mastery bounded and evidence idempotent', async () => {
    await exec(`INSERT INTO student_profiles(user_id) VALUES('${student}')`);
    await rejects(`INSERT INTO topic_mastery(student_id,topic_id,mastery,algorithm_version) VALUES('${student}','${topic}',1.5,'fixture')`);
    const sql = `INSERT INTO mastery_evidence(student_id,topic_id,attempt_id,version_id,algorithm_version) VALUES('${student}','${topic}','${attempt}','${ver}','fixture')`;
    await exec(sql); await rejects(sql, '23505');
  });
  await test('private practice does not issue classroom codes', async () => {
    await exec(`INSERT INTO assessments(id,owner_id,title,kind,mode) VALUES('${practice}','${student}','Fixture practice','practice','adaptive');
      UPDATE assessments SET state='published',published_at=now() WHERE id='${practice}'`);
    await rejects(`INSERT INTO reference_codes(assessment_id,code_digest) VALUES('${practice}',repeat('e',64))`);
  });
  await test('quarantine pauses new attempts and preserves completed evidence', async () => {
    await exec(`INSERT INTO course_memberships(course_id,student_id) VALUES('${course}','${stranger}');
      UPDATE question_releases SET state='quarantined',reason='Fixture report' WHERE version_id='${ver}'`);
    await rejects(`INSERT INTO attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key)
      VALUES('${assessment}','${u}','${stranger}',1,gen_random_uuid())`);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)), 2);
  });
  await test('embedding dimensions and unit length enforced', async () => {
    await exec(`INSERT INTO embedding_models(id,model_name,revision,dimension,normalization) VALUES('${model}','fixture-local','fixture-revision',384,'l2')`);
    await rejects(`INSERT INTO embeddings(chunk_id,owner_id,model_id,embedding) VALUES('${chunk}','${u}','${model}','[1,0,0]')`, '22000');
    const zero = JSON.stringify(Array(384).fill(0));
    await rejects(`INSERT INTO embeddings(chunk_id,owner_id,model_id,embedding) VALUES('${chunk}','${u}','${model}','${zero}')`);
  });
  await test('exact vector search filters owner before result selection', async () => {
    const embedding = JSON.stringify([1, ...Array(383).fill(0)]);
    await db.query('INSERT INTO embeddings(chunk_id,owner_id,model_id,embedding) VALUES($1,$2,$3,$4)', [chunk,u,model,embedding]);
    const sql = 'SELECT chunk_id FROM mcq.embeddings WHERE owner_id=$1 AND model_id=$2 ORDER BY embedding <=> $3::vector LIMIT 3';
    assert.equal((await db.query(sql, [u,model,embedding])).rows[0].chunk_id, chunk);
    assert.equal((await db.query(sql, [stranger,model,embedding])).rows.length, 0);
  });
  await test('failed multi-migration transaction leaves no core schema', async () => {
    const broken = new PGlite();
    try {
      let failed = false;
      try { await broken.exec(render()); } catch { failed = true; await broken.exec('ROLLBACK'); }
      assert.ok(failed, 'Expected unavailable pgvector to fail');
      assert.equal((await broken.query("SELECT count(*)::int AS n FROM pg_namespace WHERE nspname='mcq'")).rows[0].n, 0);
      await broken.exec(render(1));
      assert.equal((await broken.query('SELECT count(*)::int AS n FROM mcq_meta.schema_migrations')).rows[0].n, 1);
    } finally { await broken.close(); }
  });
  await test('populated phase 11 schema upgrades to validation gates without erasing history', async () => {
    await exec(render(5));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),5);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    await rejects(`UPDATE question_releases SET state='approved' WHERE version_id='${ver}'`);
    await exec(`UPDATE question_releases SET state='quarantined' WHERE version_id='${ver}'`);
    await exec(render(5));
  });
  await test('teacher review migration preserves historical scores and legacy evidence', async () => {
    await exec(render(6));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),6);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    assert.equal(await scalar(`SELECT teacher_review_id FROM question_releases WHERE version_id='${ver}'`),null);
    assert.ok(await scalar(`SELECT verification_id FROM question_releases WHERE version_id='${ver}'`));
    await exec(render(6));
  });
  await test('assessment migration preserves historical scores and replays safely', async () => {
    await exec(render(7));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),7);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    assert.equal(await scalar(`SELECT revision FROM assessments WHERE id='${assessment}'`),1);
    assert.equal(await scalar('SELECT count(*)::int FROM assessment_operations'),0);
    await exec(render(7));
  });
  await test('attempt and adaptive migrations preserve historical scores and replay', async () => {
    await exec(render(9));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),9);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    assert.equal(await scalar(`SELECT flagged FROM answers WHERE attempt_id='${attempt}'`),false);
    await exec(render(9));
  });
  await test('feedback migration preserves historical records and replays', async () => {
    const reports = await scalar('SELECT count(*)::int FROM feedback');
    await exec(render(10));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),10);
    assert.equal(await scalar('SELECT count(*)::int FROM feedback'),reports);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    await exec(render(10));
  });
  await test('analytics migration preserves scores, replays and denies public execution', async () => {
    await exec(render(11));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),11);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    assert.equal(await scalar("SELECT has_function_privilege('public','mcq.analytics_data(uuid,text,uuid,integer,integer,boolean)','EXECUTE')"),false);
    await exec(render(11));
  });
  await test('evaluation migration preserves scores, replays and denies public execution', async () => {
    await exec(render(12));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),12);
    assert.equal(Number(await scalar(`SELECT awarded_points FROM attempt_scores WHERE attempt_id='${attempt}'`)),2);
    assert.equal(await scalar("SELECT has_function_privilege('public','mcq.evaluation_access(uuid,text,uuid,uuid,jsonb)','EXECUTE')"),false);
    assert.equal(await scalar("SELECT has_function_privilege('public','mcq.evaluation_events(uuid,uuid[])','EXECUTE')"),false);
    await exec(render(12));
  });
  await test('teacher signup migration replays and keeps public execution revoked', async () => {
    await exec(render(13));
    assert.equal(await scalar('SELECT count(*)::int FROM mcq_meta.schema_migrations'),13);
    assert.equal(await scalar("SELECT has_function_privilege('public','mcq.register_teacher(text,text,text)','EXECUTE')"),false);
    await exec(render(13));
  });
  console.log(`\n${passed} database checks passed. Fixtures are synthetic, not project evaluation results.`);
} finally { await db.close(); }

