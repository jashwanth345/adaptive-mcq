// Synthetic SQL integrity fixtures, never measurements of model quality.
import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const db = new PGlite({ extensions: { vector } });
let passed = 0;
const exec = sql => db.exec(sql);
async function check(name, fn) { await fn(); passed++; console.log(`PASS ${name}`); }
async function rejects(sql, code = '23514') {
  let caught;
  try { await exec(sql); } catch (error) { caught = error; }
  await exec('ROLLBACK');
  assert.ok(caught, 'Expected rejection'); assert.equal(caught.code, code, caught.message);
}
const owner = randomUUID(), other = randomUUID(), topic = randomUUID(), material = randomUUID(), document = randomUUID(), chunk = randomUUID();
async function draft({ mode = 'ollama', type = 'conceptual', blind = 0 } = {}) {
  const d = Object.fromEntries(['q','v','job','run','reviewJob','review','core'].map(k => [k,randomUUID()]));
  await exec(`BEGIN;
    INSERT INTO mcq.jobs(id,owner_id,kind,state,idempotency_key) VALUES('${d.job}','${owner}','generate','completed',gen_random_uuid()),('${d.reviewJob}','${owner}','verify','completed',gen_random_uuid());
    INSERT INTO mcq.generation_runs(id,owner_id,job_id,generator_model,model_digest,prompt_version,settings) VALUES('${d.run}','${owner}','${d.job}','fixture','fixture','fixture','{"mode":"${mode}"}');
    INSERT INTO mcq.questions(id,owner_id) VALUES('${d.q}','${owner}');
    INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type)
    VALUES('${d.v}','${d.q}','${owner}',1,'${topic}','${d.run}','Synthetic stem ${d.v}','Synthetic explanation',0,'easy','remember','${type}');
    INSERT INTO mcq.options(version_id,ordinal,content) SELECT '${d.v}',n,'Option '||n FROM generate_series(0,3) n;
    INSERT INTO mcq.question_sources VALUES('${d.v}','${chunk}','${owner}','Fixture evidence');
    INSERT INTO mcq.verifier_reports(id,owner_id,version_id,job_id,mode,recommendation,result) VALUES('${d.review}','${owner}','${d.v}','${d.reviewJob}','${mode}','${mode === 'mock' ? 'NOT_EVALUATED' : 'PASS'}','{"ai_executed":${mode === 'ollama'},"blind_option":${blind}}');
    INSERT INTO mcq.question_verifications(id,version_id,verifier_model,model_digest,prompt_version,policy_version,status,confidence_score,correctness_score,clarity_score,difficulty_score,distractor_score,grounding_score,duplicate_score,blind_option,schema_pass,source_pass,duplicate_pass,math_result,review_required)
    VALUES('${d.core}','${d.v}','fixture','fixture','fixture','fixture','PASS',80,80,80,80,80,80,0,0,true,true,true,'${type === 'numerical' ? 'pass' : 'not_applicable'}',false);
    COMMIT;`);
  return d;
}
function report(d, { id = randomUUID(), ready = true, review = d.review, corpus, math = 'not_applicable', duplicate = 'pass', account = owner } = {}) {
  return `INSERT INTO mcq.validation_reports(id,owner_id,version_id,idempotency_key,policy_version,verifier_report_id,corpus_hash,schema_pass,source_pass,duplicate_status,math_status,technical_pass,result)
    VALUES('${id}','${account}','${d.v}',gen_random_uuid(),'deterministic-validation-v1',${review ? `'${review}'` : 'NULL'},${corpus ? `'${corpus}'` : `mcq.validation_corpus('${account}','${d.q}')`},true,true,'${duplicate}','${math}',${ready},'{}')`;
}
const release = (d, reviewer = owner) => `INSERT INTO mcq.question_releases(version_id,verification_id,reviewed_by,state) VALUES('${d.v}','${d.core}',${reviewer ? `'${reviewer}'` : 'NULL'},'approved')`;
async function assessment(d) {
  const aid=randomUUID(), course=randomUUID();
  await exec(`INSERT INTO mcq.courses(id,owner_id,title) VALUES('${course}','${owner}','Course ${course}');
    INSERT INTO mcq.assessments(id,owner_id,course_id,title,kind,mode) VALUES('${aid}','${owner}','${course}','Test assessment','classroom','fixed');
    INSERT INTO mcq.assessment_questions VALUES('${aid}','${owner}',1,'${d.v}',1)`);
  return `UPDATE mcq.assessments SET state='published',published_at=now() WHERE id='${aid}'`;
}
try {
  const sql=spawnSync(process.env.TEST_PYTHON || 'python',[fileURLToPath(new URL('../migrate.py',import.meta.url)),'render'],{encoding:'utf8'});
  assert.equal(sql.status,0,sql.stderr); await exec(sql.stdout);
  await exec(`INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES('${owner}','validation.teacher@example.invalid','Fixture teacher','synthetic-hash-not-a-login'),('${other}','validation.student@example.invalid','Fixture student','synthetic-hash-not-a-login');
    INSERT INTO mcq.user_roles VALUES('${owner}','teacher'),('${other}','student');
    INSERT INTO mcq.topics(id,owner_id,name) VALUES('${topic}','${owner}','Fixture');
    INSERT INTO mcq.materials(id,owner_id,title) VALUES('${material}','${owner}','Fixture');
    INSERT INTO mcq.documents(id,material_id,owner_id,version,storage_key,sha256,byte_size,page_count) VALUES('${document}','${material}','${owner}',1,'fixture.pdf',repeat('a',64),10,1);
    INSERT INTO mcq.chunks(id,document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version) VALUES('${chunk}','${document}','${owner}',0,1,1,'Fixture evidence',repeat('b',64),2,'fixture')`);
  await check('release without validation evidence is rejected',async()=>{ const d=await draft(); await rejects(release(d)); });
  await check('test generation cannot receive technical readiness',async()=>{ const d=await draft({mode:'mock'}); await rejects(report(d)); await exec(report(d,{ready:false})); await rejects(release(d)); });
  await check('missing verifier evidence cannot pass',async()=>{ const d=await draft(); await rejects(report(d,{review:null})); });
  await check('wrong blind answer cannot pass',async()=>{ const d=await draft({blind:1}); await rejects(report(d)); });
  await check('failed and unsupported math cannot pass',async()=>{ const d=await draft({type:'numerical'}); for(const math of ['fail','unsupported','not_applicable']) await rejects(report(d,{math})); await exec(report(d,{math:'pass'})); });
  await check('failed and incomplete duplicate checks cannot pass',async()=>{ const d=await draft(); for(const duplicate of ['fail','incomplete']) await rejects(report(d,{duplicate})); });
  await check('foreign draft verifier and owner cannot be attached',async()=>{ const a=await draft(),b=await draft(); await rejects(report(a,{review:b.review})); await rejects(report(a,{ready:false,review:null,account:other}),'23503'); });
  await check('stale corpus cannot be recorded as ready',async()=>{ const d=await draft(); await rejects(report(d,{corpus:'0'.repeat(32)})); });
  await check('saved reports are immutable and cannot grant publication',async()=>{ const d=await draft(),id=randomUUID(); await exec(report(d,{id})); await rejects(`UPDATE mcq.validation_reports SET publication_eligible=true WHERE id='${id}'`); await rejects(`DELETE FROM mcq.validation_reports WHERE id='${id}'`); });
  await check('ready evidence still needs owning teacher',async()=>{ const d=await draft(); await exec(report(d)); await rejects(release(d,null)); await rejects(release(d,other)); await exec(`DELETE FROM mcq.user_roles WHERE user_id='${owner}' AND role='teacher'`); await rejects(release(d)); await exec(`INSERT INTO mcq.user_roles VALUES('${owner}','teacher')`); });
  await check('latest failed validation supersedes older pass',async()=>{ const d=await draft(); await exec(report(d)); await exec(report(d,{ready:false,duplicate:'fail'})); await rejects(release(d)); });
  await check('new verifier report invalidates prior validation',async()=>{ const d=await draft(); await exec(report(d)); const job=randomUUID(); await exec(`INSERT INTO mcq.jobs(id,owner_id,kind,state,idempotency_key) VALUES('${job}','${owner}','verify','completed',gen_random_uuid()); INSERT INTO mcq.verifier_reports(owner_id,version_id,job_id,mode,recommendation,result,created_at) VALUES('${owner}','${d.v}','${job}','ollama','REJECT','{"ai_executed":true}',clock_timestamp())`); await rejects(release(d)); });
  await check('new same-owner question invalidates comparison evidence',async()=>{ const d=await draft(); await exec(report(d)); await draft(); await rejects(release(d)); });
  await check('matching current evidence permits reviewed release and publication',async()=>{ const d=await draft(); await exec(report(d)); await exec(release(d)); await exec(await assessment(d)); });
  await check('publication rechecks stale evidence while quarantine remains possible',async()=>{ const d=await draft(); await exec(report(d)); await exec(release(d)); const publish=await assessment(d); await draft(); await rejects(publish); await exec(`UPDATE mcq.question_releases SET state='quarantined',reason='Stale evidence' WHERE version_id='${d.v}'`); });
  await check('another account does not change owned corpus',async()=>{ const d=await draft(); await exec(report(d)); const q=randomUUID(),t=randomUUID(),v=randomUUID(); await exec(`BEGIN; INSERT INTO mcq.topics(id,owner_id,name) VALUES('${t}','${other}','Private'); INSERT INTO mcq.questions(id,owner_id) VALUES('${q}','${other}'); INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type) VALUES('${v}','${q}','${other}',1,'${t}','Private stem','Private explanation',0,'easy','remember','conceptual'); INSERT INTO mcq.options(version_id,ordinal,content) SELECT '${v}',n,'Other '||n FROM generate_series(0,3)n; COMMIT;`); await exec(release(d)); });
  await check('a newer edit invalidates readiness of the previous version',async()=>{ const d=await draft(); await exec(report(d)); const v=randomUUID(); await exec(`BEGIN; INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type) VALUES('${v}','${d.q}','${owner}',2,'${topic}','${d.run}','Edited stem','Edited explanation',0,'easy','remember','conceptual'); INSERT INTO mcq.options(version_id,ordinal,content) SELECT '${v}',n,'Edited '||n FROM generate_series(0,3)n; COMMIT;`); await rejects(release(d)); await rejects(report(d)); });
  await check('archived source prevents release of a previously ready question',async()=>{ const d=await draft(); await exec(report(d)); await exec(`UPDATE mcq.materials SET archived=true WHERE id='${material}'`); await rejects(release(d)); await exec(`UPDATE mcq.materials SET archived=false WHERE id='${material}'`); });
  await check('disabled teacher cannot approve ready content',async()=>{ const d=await draft(); await exec(report(d)); await exec(`UPDATE mcq.users SET active=false WHERE id='${owner}'`); await rejects(release(d)); await exec(`UPDATE mcq.users SET active=true WHERE id='${owner}'`); });
  await check('student automatic practice release cannot be used for a classroom test',async()=>{ const d=await draft(); await exec(report(d)); await exec(`INSERT INTO mcq.user_roles VALUES('${owner}','student')`); await exec(release(d,null)); await rejects(await assessment(d)); const a=randomUUID(); await exec(`INSERT INTO mcq.assessments(id,owner_id,title,kind,mode) VALUES('${a}','${owner}','Private fixture','practice','fixed'); INSERT INTO mcq.assessment_questions VALUES('${a}','${owner}',1,'${d.v}',1); UPDATE mcq.assessments SET state='published',published_at=now() WHERE id='${a}'`); });
  const action = async (d, operation, body = {note:'Synthetic teacher review note'}, key = randomUUID(), account = owner) =>
    (await db.query('SELECT mcq.teacher_review_action($1,$2,$3,$4,$5::jsonb) AS result',[account,d.v,key,operation,JSON.stringify(body)])).rows[0].result;
  const editFields = {note:'Clarify the synthetic question',stem:'Which process reduces redundant data?',explanation:'Normalization reduces redundant data.',options:['Normalization','Replication','Indexing','Sorting'],correct_option:0,difficulty:'easy',cognitive_level:'understand'};
  await check('categorical approval stores exact report without a legacy verification pointer', async()=>{
    const d=await draft(),rid=randomUUID(); await exec(report(d,{id:rid}));
    assert.equal((await action(d,'approve')).version_id,d.v);
    const r=(await db.query(`SELECT r.verification_id,e.validation_report_id FROM mcq.question_releases r JOIN mcq.teacher_review_events e ON e.id=r.teacher_review_id WHERE r.version_id='${d.v}'`)).rows[0];
    assert.equal(r.verification_id,null); assert.equal(r.validation_report_id,rid); await exec(await assessment(d));
  });
  await check('new validation requires renewed teacher approval before publication',async()=>{
    const d=await draft(); await exec(report(d)); await action(d,'approve'); const publish=await assessment(d);
    await exec(report(d)); await rejects(publish); await action(d,'approve'); await exec(publish);
  });
  await check('reject quarantines a release and cannot be bypassed through the legacy path',async()=>{
    const d=await draft(); await exec(report(d)); await action(d,'approve'); await action(d,'reject');
    assert.equal((await action(d,'approve')).error,'TEACHER_REVIEW_REJECTED');
    await rejects(`UPDATE mcq.question_releases SET state='approved',verification_id='${d.core}',teacher_review_id=NULL WHERE version_id='${d.v}'`);
    assert.equal((await db.query(`SELECT state FROM mcq.question_releases WHERE version_id='${d.v}'`)).rows[0].state,'quarantined');
  });
  await check('editing quarantines the previous release and never inherits reports',async()=>{
    const d=await draft(); await exec(report(d)); await action(d,'approve'); const key=randomUUID();
    const edited=await action(d,'edit',editFields,key); assert.ok(edited.version_id);
    assert.deepEqual(await action(d,'edit',editFields,key),edited);
    assert.equal((await action(d,'edit',{...editFields,note:'Different note'},key)).error,'TEACHER_REVIEW_KEY_CONFLICT');
    assert.equal((await action(d,'edit',editFields)).error,'TEACHER_REVIEW_STALE');
    assert.equal((await db.query(`SELECT state FROM mcq.question_releases WHERE version_id='${d.v}'`)).rows[0].state,'quarantined');
    assert.equal((await action({v:edited.version_id},'approve')).error,'TEACHER_APPROVAL_BLOCKED');
    await rejects(`UPDATE mcq.teacher_review_events SET action='reject' WHERE version_id='${edited.version_id}'`);
  });
  await check('reviewed source links are sealed before teacher approval',async()=>{
    const d=await draft(); await rejects(`INSERT INTO mcq.question_sources VALUES('${d.v}','${chunk}','${owner}','Different quote')`);
  });
  await check('teacher functions deny other owners, student-only accounts and inactive users',async()=>{
    const d=await draft(); await exec(report(d)); assert.equal((await action(d,'approve',undefined,undefined,other)).error,'TEACHER_REVIEW_NOT_FOUND');
    await exec(`DELETE FROM mcq.user_roles WHERE user_id='${owner}' AND role='teacher'`);
    assert.equal((await action(d,'approve')).error,'TEACHER_REVIEW_FORBIDDEN');
    await exec(`INSERT INTO mcq.user_roles VALUES('${owner}','teacher'); UPDATE mcq.users SET active=false WHERE id='${owner}'`);
    assert.equal((await action(d,'approve')).error,'TEACHER_REVIEW_FORBIDDEN'); await exec(`UPDATE mcq.users SET active=true WHERE id='${owner}'`);
  });
  await check('temporary shadow tables cannot replace approval evidence',async()=>{
    const d=await draft(); await exec(report(d));
    await exec('CREATE TEMP TABLE question_versions (spoof text); CREATE TEMP TABLE validation_reports (spoof text)');
    assert.equal((await db.query(`SELECT mcq.teacher_approval_ready('${owner}','${d.v}') AS ready`)).rows[0].ready,true);
    assert.equal((await action(d,'approve')).version_id,d.v);
    await exec('DROP TABLE pg_temp.question_versions; DROP TABLE pg_temp.validation_reports');
  });
  await check('audit failure atomically rolls back the new version and teacher event',async()=>{
    const d=await draft(); const before=(await db.query('SELECT count(*)::int AS n FROM mcq.teacher_review_events')).rows[0].n;
    await exec("CREATE FUNCTION mcq.fixture_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture audit failure'; END $$; CREATE TRIGGER fixture_fail_audit BEFORE INSERT ON mcq.audit_events FOR EACH ROW EXECUTE FUNCTION mcq.fixture_fail_audit()");
    await assert.rejects(()=>action(d,'edit',editFields),/fixture audit failure/);
    assert.equal((await db.query(`SELECT count(*)::int AS n FROM mcq.question_versions WHERE question_id='${d.q}'`)).rows[0].n,1);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM mcq.teacher_review_events')).rows[0].n,before);
    await exec('DROP TRIGGER fixture_fail_audit ON mcq.audit_events; DROP FUNCTION mcq.fixture_fail_audit()');
  });
  const d=await draft(); await exec(report(d)); await action(d,'approve');
  const course=randomUUID(), student=randomUUID();
  await exec(`INSERT INTO mcq.courses(id,owner_id,title) VALUES('${course}','${owner}','Publication fixture');
    INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES('${student}','publication@example.com','Synthetic student','synthetic-hash-not-a-login');
    INSERT INTO mcq.user_roles VALUES('${student}','student')`);
  const change=async(target,op,body={},digest=null,key=randomUUID())=>(await db.query(
    'SELECT mcq.assessment_action($1,$2,$3,$4,$5::jsonb,$6) AS result',[owner,target,key,op,JSON.stringify(body),digest])).rows[0].result;
  const joined=async(hash)=>(await db.query('SELECT mcq.join_assessment($1,$2) AS result',[student,hash])).rows[0].result;
  const created=await change(null,'create',{course_id:course,title:'Publication fixture',version_ids:[d.v],time_limit_seconds:null,max_attempts:2,randomize_questions:false,randomize_options:false,release_policy:'after_submit'});
  const aid=created.assessment_id; assert.ok(aid);
  const attemptSQL=()=>`INSERT INTO mcq.attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key) VALUES('${aid}','${owner}','${student}',1,gen_random_uuid())`;
  await check('failed code expiry validation rolls publication back to draft',async()=>{
    assert.equal((await change(aid,'publish',{revision:1,expiry_hours:0},'1'.repeat(64))).error,'ASSESSMENT_INVALID');
    assert.equal((await db.query('SELECT state FROM mcq.assessments WHERE id=$1',[aid])).rows[0].state,'draft');
  });
  await check('publication and initial digest issuance are one transaction',async()=>{
    const result=await change(aid,'publish',{revision:1,expiry_hours:24},'1'.repeat(64)); assert.ok(result.code_id);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM mcq.reference_codes WHERE assessment_id=$1',[aid])).rows[0].n,1);
  });
  await check('published questions and settings cannot be mutated',async()=>{
    await rejects(`UPDATE mcq.assessments SET max_attempts=50 WHERE id='${aid}'`);
    await rejects(`DELETE FROM mcq.assessment_questions WHERE assessment_id='${aid}'`);
  });
  await check('collision rollback preserves the previously working code',async()=>{
    assert.equal((await change(aid,'rotate',{expiry_hours:24},'1'.repeat(64))).error,'CODE_COLLISION');
    assert.equal((await db.query('SELECT revoked_at FROM mcq.reference_codes WHERE assessment_id=$1',[aid])).rows[0].revoked_at,null);
  });
  await check('course membership alone cannot bypass the new code admission gate',async()=>{
    await exec(`INSERT INTO mcq.course_memberships(course_id,student_id) VALUES('${course}','${student}')`);
    await rejects(attemptSQL());
    assert.equal((await joined('1'.repeat(64))).error,'ASSESSMENT_UNAVAILABLE');
    await change(aid,'participant',{email:'publication@example.com',active:true});
    assert.equal((await joined('1'.repeat(64))).assessment_id,aid);
  });
  await check('revoked admission blocks new attempts without deleting admission history',async()=>{
    await change(aid,'revoke'); await rejects(attemptSQL());
    assert.equal((await db.query('SELECT count(*)::int AS n FROM mcq.assessment_admissions WHERE assessment_id=$1',[aid])).rows[0].n,1);
  });
  await check('new code admission permits a stored attempt and enforces the maximum',async()=>{
    await change(aid,'rotate',{expiry_hours:24},'2'.repeat(64)); await joined('2'.repeat(64));
    await exec(attemptSQL());
    await exec(`INSERT INTO mcq.attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key) VALUES('${aid}','${owner}','${student}',2,gen_random_uuid())`);
    assert.equal((await joined('2'.repeat(64))).error,'ASSESSMENT_UNAVAILABLE');
    await rejects(attemptSQL());
  });
  await check('closing preserves existing attempts and revokes codes',async()=>{
    await change(aid,'close');
    assert.equal((await db.query('SELECT count(*)::int AS n FROM mcq.attempts WHERE assessment_id=$1',[aid])).rows[0].n,2);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM mcq.reference_codes WHERE assessment_id=$1 AND revoked_at IS NULL',[aid])).rows[0].n,0);
  });
  console.log(`${passed} validation/teacher/assessment database gate checks passed. Synthetic evidence only.`);
} finally { await db.close(); }
