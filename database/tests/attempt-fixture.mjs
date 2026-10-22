// Disposable synthetic evidence only. Never imported by application code.
import { randomUUID, createHash } from 'node:crypto';

export async function seedAttemptFixture(db, teacher, passwordHash, documentFixture = null) {
  const student = randomUUID(), course = randomUUID();
  await db.query("INSERT INTO mcq.users(id,email,display_name,password_hash) VALUES($1,'attempt.student@example.com','Attempt Student',$2)",[student,passwordHash]);
  await db.query("INSERT INTO mcq.user_roles VALUES($1,'student');",[student]);
  await db.query('INSERT INTO mcq.student_profiles(user_id) VALUES($1)',[student]);
  await db.query("INSERT INTO mcq.courses(id,owner_id,title) VALUES($1,$2,'Synthetic DBMS course')",[course,teacher]);
  const versions=[];
  for (const [account,count] of [[teacher,3],[student,1]]) {
    const topic=randomUUID(), material=randomUUID(), document=randomUUID(), chunk=randomUUID(), rows=[];
    await db.query("INSERT INTO mcq.topics(id,owner_id,name) VALUES($1,$2,'DBMS fixture')",[topic,account]);
    await db.query("INSERT INTO mcq.materials(id,owner_id,title) VALUES($1,$2,'Synthetic source')",[material,account]);
    const source = documentFixture ? await documentFixture(document) : { key: document+'.pdf', sha256: 'a'.repeat(64), size: 10 };
    await db.query("INSERT INTO mcq.documents(id,material_id,owner_id,version,storage_key,sha256,byte_size,page_count) VALUES($1,$2,$3,1,$4,$5,$6,1)",[document,material,account,source.key,source.sha256,source.size]);
    await db.query("INSERT INTO mcq.chunks(id,document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version) VALUES($1,$2,$3,0,1,1,'Normalization reduces redundant data.',repeat('b',64),5,'fixture')",[chunk,document,account]);
    for(let n=0;n<count;n++) {
      const q=randomUUID(),v=randomUUID(),job=randomUUID(),run=randomUUID(),reviewJob=randomUUID(),review=randomUUID();
      await db.exec('BEGIN');
      await db.query("INSERT INTO mcq.jobs(id,owner_id,kind,state,idempotency_key) VALUES($1,$2,'generate','completed',gen_random_uuid()),($3,$2,'verify','completed',gen_random_uuid())",[job,account,reviewJob]);
      const settings={mode:'ollama',synthetic_test:true,model:'synthetic-fixture',retrieval:'semantic',citation:'S1',evidence_quote:'Normalization reduces redundant data.',sources:[{citation:'S1',material_id:material,title:'Synthetic source',document_id:document,chunk_id:chunk,page_start:1,page_end:1,similarity:1,content_sha256:'b'.repeat(64),excerpt_sha256:'b'.repeat(64),excerpt:'Normalization reduces redundant data.',clipped:false}]};
      await db.query(`INSERT INTO mcq.generation_runs(id,owner_id,job_id,generator_model,model_digest,prompt_version,settings) VALUES($1,$2,$3,'synthetic-fixture','fixture','fixture',$4::jsonb)`,[run,account,job,JSON.stringify(settings)]);
      await db.query('INSERT INTO mcq.questions(id,owner_id) VALUES($1,$2)',[q,account]);
      await db.query("INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type) VALUES($1,$2,$3,1,$4,$5,$6,'Normalization reduces redundant data. Synthetic test explanation.',0,'easy','understand','conceptual')",[v,q,account,topic,run,`Synthetic question ${n+1}: Which method reduces redundant data?`]);
      await db.query("INSERT INTO mcq.options(version_id,ordinal,content) VALUES($1,0,'Normalization'),($1,1,'Replication'),($1,2,'Sorting'),($1,3,'Indexing')",[v]);
      await db.query("INSERT INTO mcq.question_sources VALUES($1,$2,$3,'Normalization reduces redundant data.')",[v,chunk,account]);
      await db.query(`INSERT INTO mcq.verifier_reports(id,owner_id,version_id,job_id,mode,recommendation,result) VALUES($1,$2,$3,$4,'ollama','PASS','{"ai_executed":true,"blind_option":0,"synthetic_test":true}')`,[review,account,v,reviewJob]);
      await db.exec('COMMIT'); rows.push({q,v,review});
    }
    // Final validation after all fixture versions exist, so corpus hashes are current.
    for (const row of rows) {
      const validation={synthetic_test:true,checks:[],math:{status:'not_applicable',computed:null,matching_options:[],detail:'Synthetic conceptual fixture'},duplicates:{status:'pass',complete:true,scanned:0,match_count:0,matches:[],detail:'Synthetic workflow evidence, not a measured duplicate test'},blockers:[]};
      await db.query("INSERT INTO mcq.validation_reports(owner_id,version_id,idempotency_key,policy_version,verifier_report_id,corpus_hash,schema_pass,source_pass,duplicate_status,math_status,technical_pass,result) VALUES($1,$2,gen_random_uuid(),'deterministic-validation-v1',$3,mcq.validation_corpus($1,$4),true,true,'pass','not_applicable',true,$5::jsonb)",[account,row.v,row.review,row.q,JSON.stringify(validation)]);
      if(account===teacher) {
        const decision=(await db.query(`SELECT mcq.teacher_review_action($1,$2,gen_random_uuid(),'approve','{"note":"Synthetic approval for workflow tests"}') AS result`,[teacher,row.v])).rows[0].result;
        if(decision.error) throw new Error(decision.error);
        versions.push(row.v);
      }
    }
  }
  const body={course_id:course,title:'Synthetic classroom assessment',version_ids:versions,time_limit_seconds:600,max_attempts:2,randomize_questions:true,randomize_options:true,release_policy:'after_submit'};
  const result=(await db.query("SELECT mcq.assessment_action($1,NULL,gen_random_uuid(),'create',$2::jsonb,NULL) AS result",[teacher,JSON.stringify(body)])).rows[0].result;
  if(result.error) throw new Error(result.error);
  const aid=result.assessment_id, code='MCQ-1234-5678-ABCD-EF01-2345';
  await db.query(`SELECT mcq.assessment_action($1,$2,gen_random_uuid(),'participant','{"email":"attempt.student@example.com","active":true}',NULL)`,[teacher,aid]);
  const digest=createHash('sha256').update(code.replaceAll('-','')).digest('hex');
  const pub=(await db.query(`SELECT mcq.assessment_action($1,$2,gen_random_uuid(),'publish','{"revision":1,"expiry_hours":24}',$3) AS result`,[teacher,aid,digest])).rows[0].result;
  if(pub.error) throw new Error(pub.error);
  return {student,teacher,aid,code,versions};
}
