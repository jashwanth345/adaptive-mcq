// Synthetic SQL evidence, isolated from application storage and inference.
import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { randomUUID, createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { seedAttemptFixture } from './attempt-fixture.mjs';
const db=new PGlite({extensions:{vector}});let count=0;
async function check(name,run){await run();count++;console.log('PASS '+name);}
const one=async(sql,args=[]) => (await db.query(sql,args)).rows[0];
try {
 const rendered=spawnSync(process.env.TEST_PYTHON||'python',[fileURLToPath(new URL('../migrate.py',import.meta.url)),'render'],{encoding:'utf8'});
 assert.equal(rendered.status,0,rendered.stderr);await db.exec(rendered.stdout);
 const teacher=randomUUID();await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,'teacher@example.com','Synthetic teacher','synthetic-hash-not-a-login')",[teacher]);await db.query("INSERT INTO mcq.user_roles VALUES($1,'teacher')",[teacher]);
 const f=await seedAttemptFixture(db,teacher,'synthetic-hash-not-a-login');
 await db.query('SELECT mcq.join_assessment($1,$2)',[f.student,createHash('sha256').update(f.code.replaceAll('-','')).digest('hex')]);
 const attempt=async(target,op,body={}) => (await one('SELECT mcq.attempt_action($1,$2,$3,$4,$5::jsonb) AS r',[f.student,target,randomUUID(),op,JSON.stringify(body)])).r;
 const action=async(account,target,op,body={},key=randomUUID()) => (await one('SELECT mcq.feedback_action($1,$2,$3,$4,$5::jsonb) AS r',[account,target,key,op,JSON.stringify(body)])).r;
 const detail=async(v=f.versions[0],account=teacher) => (await one('SELECT mcq.feedback_detail($1,$2,0,20) AS r',[account,v])).r;
 const id=(await attempt(f.aid,'start')).attempt_id;
 await attempt(id,'submit',{revision:1});
 const body={version_id:f.versions[0],category:'wrong_answer',comment:'Synthetic concern'};
 await check('report plus audit rollback atomically on internal failure',async()=>{
  await db.exec("CREATE FUNCTION mcq.fail_feedback_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='feedback.reported' THEN RAISE EXCEPTION 'fixture fault'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_feedback BEFORE INSERT ON mcq.audit_events FOR EACH ROW EXECUTE FUNCTION mcq.fail_feedback_audit()");
  await assert.rejects(action(f.student,id,'report',body),/fixture fault/);
  assert.equal((await one('SELECT count(*)::int AS n FROM mcq.feedback')).n,0);
  assert.equal((await one('SELECT count(*)::int AS n FROM mcq.feedback_cases')).n,0);
  assert.equal((await one('SELECT count(*)::int AS n FROM mcq.feedback_commands')).n,0);
  await db.exec('DROP TRIGGER fail_feedback ON mcq.audit_events');
 });
 await action(f.student,id,'report',body);
 const second=(await attempt(f.aid,'start')).attempt_id;
 await check('exposure counts use distinct students across attempts and categories',async()=>{
  await action(f.student,id,'report',{...body,category:'ambiguous'});
  const d=await detail();assert.equal(d.summary.exposures,1);assert.equal(d.summary.reporters,1);assert.equal(d.summary.open_reporters,1);assert.equal(d.total_reports,2);
 });
 await check('confirmation rollback cannot leave partial quarantine',async()=>{
  await db.exec("CREATE FUNCTION mcq.fail_confirm_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='feedback.confirm_defect' THEN RAISE EXCEPTION 'fixture confirm fault'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_confirm BEFORE INSERT ON mcq.audit_events FOR EACH ROW EXECUTE FUNCTION mcq.fail_confirm_audit()");
  const d=await detail();await assert.rejects(action(teacher,f.versions[0],'confirm_defect',{revision:d.summary.revision,note:'Synthetic confirmed defect'}),/fixture confirm fault/);
  const after=await detail();assert.equal(after.summary.confirmed_defect,false);assert.equal(after.summary.release_state,'approved');assert.equal(after.decisions.length,0);
  await db.exec('DROP TRIGGER fail_confirm ON mcq.audit_events');
 });
 await check('confirmed defects cannot be reapproved even with direct operator SQL',async()=>{
  const d=await detail();await action(teacher,f.versions[0],'confirm_defect',{revision:d.summary.revision,note:'Synthetic confirmed defect'});
  await assert.rejects(db.query("UPDATE mcq.question_releases SET state='approved' WHERE version_id=$1",[f.versions[0]]),/Confirmed defect/);
  assert.equal((await detail()).summary.release_state,'quarantined');
 });
 await check('late completion reopens acknowledged score review without rewriting scores',async()=>{
  const d=await detail();await action(teacher,f.versions[0],'acknowledge_grades',{revision:d.summary.revision,note:'Reviewed original score; correction pending'});
  assert.equal((await detail()).summary.grade_review,'acknowledged');
  await attempt(second,'submit',{revision:1});assert.equal((await detail()).summary.grade_review,'pending');assert.equal((await detail()).summary.completed_attempts,2);
  const duplicate=await action(f.student,second,'report',body);assert.equal(duplicate.duplicate,true);assert.equal((await detail()).total_reports,2);
 });
 await check('private owners review only their own practice content',async()=>{
  const v=(await one('SELECT id FROM mcq.question_versions WHERE owner_id=$1',[f.student])).id;
  const a=(await attempt(v,'practice')).attempt_id;assert.ok(a);await attempt(a,'submit',{revision:1});
  await action(f.student,a,'report',{version_id:v,category:'rating',rating:'poor'});
  assert.equal((await detail(v,teacher)).error,'FEEDBACK_NOT_FOUND');
  const d=await detail(v,f.student);assert.equal(d.summary.poor,1);
  await action(f.student,v,'confirm_defect',{revision:d.summary.revision,note:'Private question is defective'});
  assert.equal((await attempt(v,'practice')).error,'PRACTICE_BLOCKED');
 });
 await check('restricted role has no direct report/decision/release writes',async()=>{
  await db.exec('CREATE ROLE feedback_runtime; GRANT USAGE ON SCHEMA mcq TO feedback_runtime; GRANT EXECUTE ON FUNCTION mcq.feedback_action(uuid,uuid,uuid,text,jsonb),mcq.feedback_queue(uuid,integer,integer),mcq.feedback_detail(uuid,uuid,integer,integer),mcq.feedback_history(uuid,integer,integer) TO feedback_runtime');
  for(const table of ['feedback','feedback_cases','feedback_decisions','feedback_commands','question_releases']) assert.equal((await one("SELECT has_table_privilege('feedback_runtime',$1,'INSERT,UPDATE,DELETE') AS p",['mcq.'+table])).p,false);
  assert.equal((await one("SELECT has_function_privilege('feedback_runtime','mcq.feedback_case_summary(uuid)','EXECUTE') AS p")).p,false);
 });
 await check('revoked teacher role cannot review classroom reports through a retained student role',async()=>{
  await db.query("INSERT INTO mcq.user_roles VALUES($1,'student')",[teacher]);
  await db.query("DELETE FROM mcq.user_roles WHERE user_id=$1 AND role='teacher'",[teacher]);
  assert.equal((await detail()).error,'FEEDBACK_NOT_FOUND');
  assert.equal((await one('SELECT mcq.feedback_queue($1,0,20) AS r',[teacher])).r.total,0);
  assert.equal((await action(teacher,f.versions[0],'review',{revision:1,note:'Unauthorized review'})).error,'FEEDBACK_NOT_FOUND');
 });
 console.log(`${count} feedback database checks passed. Synthetic evidence only.`);
}finally{await db.close();}
