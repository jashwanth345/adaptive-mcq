import { PGlite } from '@electric-sql/pglite';
import { vector } from '@electric-sql/pglite-pgvector';
import { randomUUID, createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { seedAttemptFixture } from './attempt-fixture.mjs';

const db=new PGlite({extensions:{vector}}); let count=0;
async function check(label, fn) { await fn(); count++; console.log('PASS '+label); }
try {
 const rendered=spawnSync(process.env.TEST_PYTHON||'python',[fileURLToPath(new URL('../migrate.py',import.meta.url)),'render'],{encoding:'utf8'});
 assert.equal(rendered.status,0,rendered.stderr); await db.exec(rendered.stdout);
 const teacher=randomUUID(); await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,'teacher@example.com','Synthetic teacher','synthetic-hash-not-a-login')",[teacher]);
 await db.query("INSERT INTO mcq.user_roles VALUES($1,'teacher')",[teacher]);
 const f=await seedAttemptFixture(db,teacher,'synthetic-hash-not-a-login');
 const action=async(target,op,body={},key=randomUUID())=>(await db.query('SELECT mcq.attempt_action($1,$2,$3,$4,$5::jsonb) AS r',[f.student,target,key,op,JSON.stringify(body)])).rows[0].r;
 const view=async(id)=>(await db.query('SELECT mcq.attempt_view($1,$2) AS r',[f.student,id])).rows[0].r;
 const learning=async()=>(await db.query('SELECT mcq.learning_data($1) AS r',[f.student])).rows[0].r;
 let aid; const key=randomUUID();
 await check('an unauthorized start never creates an attempt',async()=>{ assert.equal((await action(f.aid,'start')).error,'ATTEMPT_UNAVAILABLE'); });
 const hash=createHash('sha256').update(f.code.replaceAll('-','')).digest('hex');
 await db.query('SELECT mcq.join_assessment($1,$2)',[f.student,hash]);
 await check('start pins permutations and retries return the same attempt',async()=>{
   aid=(await action(f.aid,'start',{},key)).attempt_id; assert.ok(aid);
   assert.equal((await action(f.aid,'start',{},key)).attempt_id,aid);
   assert.equal((await action(f.aid,'start')).attempt_id,aid);
   assert.equal((await action(randomUUID(),'start',{},key)).error,'ATTEMPT_KEY_CONFLICT');
   const a=await view(aid),b=await view(aid); assert.deepEqual(a.items,b.items); assert.equal(a.items.length,3);
   assert.equal(a.result,null); assert.ok(a.items.every(x=>!('correct_option' in x)&&!('option_order' in x)));
 });
 let saved;
 await check('display positions map to immutable keys, with stale writes rejected',async()=>{
   const a=await view(aid); const body={revision:1,answers:a.items.map(x=>({position:x.position,selected_option:x.options.indexOf('Normalization'),flagged:x.position===1}))};
   const retry=randomUUID(); assert.equal((await action(aid,'save',body,retry)).attempt_id,aid);
   assert.equal((await action(aid,'save',body,retry)).attempt_id,aid);
   assert.equal((await action(aid,'save',body)).error,'ATTEMPT_STALE');
   saved=await view(aid); assert.equal(saved.revision,2); assert.equal(saved.items[0].flagged,true);
 });
 await check('a failing audit rolls back submission and evidence together',async()=>{
   await db.exec("CREATE FUNCTION mcq.fail_attempt_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='attempt.submitted' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_attempt_audit BEFORE INSERT ON mcq.audit_events FOR EACH ROW EXECUTE FUNCTION mcq.fail_attempt_audit()");
   await assert.rejects(()=>action(aid,'submit',{revision:2}),/synthetic audit failure/);
   assert.equal((await view(aid)).state,'in_progress'); assert.equal((await learning()).evidence.length,0);
   await db.exec('DROP TRIGGER fail_attempt_audit ON mcq.audit_events; DROP FUNCTION mcq.fail_attempt_audit()');
 });
 await check('submission grades once and produces three first-exposure events',async()=>{
   const retry=randomUUID(); await action(aid,'submit',{revision:2},retry); await action(aid,'submit',{revision:2},retry); await action(aid,'submit',{revision:2});
   const result=await view(aid); assert.equal(result.state,'submitted'); assert.equal(result.result.awarded_points,3);
   assert.ok(result.items.every(x=>x.is_correct&&x.correct_option===x.selected_option)); assert.equal((await learning()).evidence.length,3);
   assert.equal((await action(aid,'save',{revision:3,answers:[]})).error,'ATTEMPT_FINISHED');
 });
 await check('expired attempts reject late choices and preserve skipped zero scores',async()=>{
   const next=(await action(f.aid,'start')).attempt_id; assert.ok(next);
   await db.query("UPDATE mcq.attempt_sessions SET deadline=clock_timestamp()-interval '1 second' WHERE attempt_id=$1",[next]);
   await action(next,'save',{revision:1,answers:[{position:1,selected_option:0,flagged:false}]});
   const v=await view(next); assert.equal(v.state,'expired'); assert.equal(v.result.awarded_points,0); assert.ok(v.items.every(x=>x.selected_option===null));
   assert.equal((await learning()).evidence.length,3); assert.equal((await action(f.aid,'start')).error,'ATTEMPT_UNAVAILABLE');
 });
 await check('quarantine removes evidence from recomputation but preserves score records',async()=>{
   await db.query("UPDATE mcq.question_releases SET state='quarantined',reason='Synthetic confirmed defect' WHERE version_id=$1",[f.versions[0]]);
   assert.equal((await learning()).evidence.length,2); assert.equal((await view(aid)).result.awarded_points,3);
 });
 await check('narrow functions do not grant direct answer or profile writes',async()=>{
   await db.exec('CREATE ROLE attempt_runtime; GRANT USAGE ON SCHEMA mcq TO attempt_runtime; GRANT EXECUTE ON FUNCTION mcq.attempt_action(uuid,uuid,uuid,text,jsonb),mcq.attempt_view(uuid,uuid),mcq.learning_data(uuid) TO attempt_runtime');
   for(const name of ['answers','attempts','attempt_items','attempt_sessions','mastery_evidence','topic_mastery']) assert.equal((await db.query("SELECT has_table_privilege('attempt_runtime',$1,'INSERT,UPDATE,DELETE') AS p",['mcq.'+name])).rows[0].p,false);
   assert.equal((await db.query("SELECT has_function_privilege('attempt_runtime','mcq.finish_attempt(uuid,boolean)','EXECUTE') AS p")).rows[0].p,false);
 });
 console.log(`${count} attempt/adaptive database checks passed. Synthetic evidence only.`);
} finally { await db.close(); }
