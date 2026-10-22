ALTER TABLE mcq.question_releases ADD COLUMN automatic_validation_id uuid REFERENCES mcq.validation_reports;
-- Replace only the Phase 13 exclusive-evidence constraint, discovered by columns.
DO $$ DECLARE c record; BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='mcq.question_releases'::regclass
   AND contype='c' AND pg_get_constraintdef(oid) LIKE '%verification_id%' AND pg_get_constraintdef(oid) LIKE '%teacher_review_id%'
 LOOP EXECUTE format('ALTER TABLE mcq.question_releases DROP CONSTRAINT %I',c.conname); END LOOP;
END $$;
ALTER TABLE mcq.question_releases ADD CHECK(num_nonnulls(verification_id,teacher_review_id,automatic_validation_id)=1);

CREATE OR REPLACE FUNCTION mcq.check_release() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE v mcq.question_verifications; q mcq.question_versions; e mcq.teacher_review_events; d mcq.validation_reports; ai mcq.verifier_reports;
BEGIN
 SELECT * INTO q FROM mcq.question_versions WHERE id=NEW.version_id;
 IF NEW.automatic_validation_id IS NOT NULL OR NEW.teacher_review_id IS NOT NULL THEN
   IF NEW.automatic_validation_id IS NOT NULL THEN
     SELECT * INTO d FROM mcq.validation_reports WHERE id=NEW.automatic_validation_id AND version_id=q.id;
     IF NEW.reviewed_by IS NOT NULL OR NOT EXISTS(SELECT 1 FROM mcq.user_roles WHERE user_id=q.owner_id AND role='student') THEN
       RAISE EXCEPTION 'Automatic release is private student practice only' USING ERRCODE='23514'; END IF;
   ELSE
     SELECT * INTO e FROM mcq.teacher_review_events WHERE id=NEW.teacher_review_id AND version_id=q.id;
     SELECT * INTO d FROM mcq.validation_reports WHERE id=e.validation_report_id AND version_id=q.id;
     IF e.id IS NULL OR e.action<>'approve' OR e.owner_id IS DISTINCT FROM NEW.reviewed_by OR e.owner_id IS DISTINCT FROM q.owner_id THEN
       RAISE EXCEPTION 'Matching teacher approval required' USING ERRCODE='23514'; END IF;
   END IF;
   SELECT * INTO ai FROM mcq.verifier_reports WHERE id=d.verifier_report_id AND version_id=q.id;
   IF d.id IS NULL OR NOT d.technical_pass OR ai.recommendation IS DISTINCT FROM 'PASS' OR ai.mode IS DISTINCT FROM 'ollama'
     OR (ai.result->'blind_option') IS DISTINCT FROM to_jsonb(q.correct_option)
     OR (q.question_type='numerical' AND d.math_status<>'pass') THEN
     RAISE EXCEPTION 'Matching real verification evidence required' USING ERRCODE='23514'; END IF;
 ELSE
   SELECT * INTO v FROM mcq.question_verifications WHERE id=NEW.verification_id AND version_id=q.id;
   IF v.id IS NULL OR v.status<>'PASS' OR v.blind_option<>q.correct_option OR (q.question_type='numerical' AND v.math_result<>'pass') THEN
     RAISE EXCEPTION 'Matching legacy verification required' USING ERRCODE='23514'; END IF;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM mcq.question_sources WHERE version_id=q.id) OR (NEW.reviewed_by IS NOT NULL AND NEW.reviewed_by<>q.owner_id) THEN
   RAISE EXCEPTION 'Owned source evidence required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

ALTER TABLE mcq.answers ADD COLUMN flagged boolean NOT NULL DEFAULT false;
CREATE TABLE mcq.attempt_sessions (
 attempt_id uuid PRIMARY KEY REFERENCES mcq.attempts,
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0),
 deadline timestamptz
);
CREATE TABLE mcq.attempt_commands (
 student_id uuid NOT NULL REFERENCES mcq.users,
 idempotency_key uuid NOT NULL,
 target_id uuid NOT NULL,
 operation text NOT NULL,
 request jsonb NOT NULL,
 attempt_id uuid NOT NULL REFERENCES mcq.attempts,
 PRIMARY KEY(student_id,idempotency_key)
);
CREATE TRIGGER preserve_attempt_command BEFORE UPDATE OR DELETE ON mcq.attempt_commands FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
REVOKE ALL ON mcq.attempt_sessions,mcq.attempt_commands FROM PUBLIC;

CREATE FUNCTION mcq.practice_ready(account uuid,target uuid) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mcq.question_versions WHERE id=target AND owner_id=account)
   OR EXISTS(SELECT 1 FROM mcq.teacher_review_events WHERE version_id=target AND action='reject')
   OR EXISTS(SELECT 1 FROM mcq.question_releases WHERE version_id=target AND state='quarantined') THEN RETURN false; END IF;
 PERFORM mcq.assert_validation_ready(target,NULL);
 RETURN true;
EXCEPTION WHEN check_violation THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION mcq.practice_ready(uuid,uuid) FROM PUBLIC;

CREATE FUNCTION mcq.finish_attempt(target uuid,timed_out boolean) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE a mcq.attempts;
BEGIN
 SELECT * INTO a FROM mcq.attempts WHERE id=target FOR UPDATE;
 IF a.state<>'in_progress' THEN RETURN; END IF;
 INSERT INTO mcq.answers(attempt_id,version_id) SELECT target,version_id FROM mcq.attempt_items WHERE attempt_id=target ON CONFLICT DO NOTHING;
 UPDATE mcq.answers ans SET is_correct=COALESCE(ans.selected_option=v.correct_option,false),
   awarded_points=CASE WHEN ans.selected_option=v.correct_option THEN i.points ELSE 0 END
 FROM mcq.attempt_items i JOIN mcq.question_versions v ON v.id=i.version_id
 WHERE ans.attempt_id=target AND i.attempt_id=target AND ans.version_id=i.version_id;
 UPDATE mcq.attempts SET state=CASE WHEN timed_out THEN 'expired' ELSE 'submitted' END,submitted_at=clock_timestamp() WHERE id=target;
 UPDATE mcq.attempt_sessions SET revision=revision+1 WHERE attempt_id=target;
 IF NOT timed_out THEN
   INSERT INTO mcq.mastery_evidence(student_id,topic_id,attempt_id,version_id,algorithm_version)
   SELECT a.student_id,v.topic_id,target,ans.version_id,'bounded-performance-v1'
   FROM mcq.answers ans JOIN mcq.question_versions v ON v.id=ans.version_id
   JOIN mcq.question_releases r ON r.version_id=v.id AND r.state='approved'
   JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.settings->>'mode'='ollama'
   WHERE ans.attempt_id=target AND ans.selected_option IS NOT NULL
     AND NOT EXISTS(SELECT 1 FROM mcq.mastery_evidence e WHERE e.student_id=a.student_id AND e.version_id=v.id)
     AND NOT EXISTS(SELECT 1 FROM mcq.attempt_items old JOIN mcq.attempts prev ON prev.id=old.attempt_id
       WHERE old.version_id=v.id AND prev.student_id=a.student_id AND prev.id<>a.id AND (prev.started_at,prev.id)<(a.started_at,a.id));
 END IF;
 INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(a.student_id,CASE WHEN timed_out THEN 'attempt.expired' ELSE 'attempt.submitted' END,'attempt',target);
END $$;
REVOKE ALL ON FUNCTION mcq.finish_attempt(uuid,boolean) FROM PUBLIC;

CREATE FUNCTION mcq.attempt_action(account uuid,target uuid,retry_key uuid,op text,body jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE prior mcq.attempt_commands; a mcq.assessments; t mcq.attempts; s mcq.attempt_sessions; q mcq.question_versions;
  aid uuid; tid uuid; owner_id_value uuid; validation_id uuid; n integer; choice jsonb; item mcq.attempt_items; stamp timestamptz;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(account::text,14));
 IF NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='student') THEN RAISE EXCEPTION 'ATTEMPT_FORBIDDEN'; END IF;
 SELECT * INTO prior FROM mcq.attempt_commands WHERE student_id=account AND idempotency_key=retry_key;
 IF prior.attempt_id IS NOT NULL THEN
   IF prior.target_id<>target OR prior.operation<>op OR prior.request<>body THEN RAISE EXCEPTION 'ATTEMPT_KEY_CONFLICT'; END IF;
   RETURN jsonb_build_object('attempt_id',prior.attempt_id);
 END IF;
 IF op='practice' THEN
   PERFORM pg_advisory_xact_lock(hashtextextended(account::text,10));
   IF NOT mcq.practice_ready(account,target) THEN RAISE EXCEPTION 'PRACTICE_BLOCKED'; END IF;
   SELECT * INTO q FROM mcq.question_versions WHERE id=target;
   -- Resume an already opened practice question instead of creating parallel copies.
   SELECT t0.id INTO tid FROM mcq.attempts t0 JOIN mcq.attempt_items i ON i.attempt_id=t0.id
     JOIN mcq.assessments a0 ON a0.id=t0.assessment_id
     WHERE t0.student_id=account AND t0.state='in_progress' AND a0.kind='practice' AND i.version_id=target
     ORDER BY t0.started_at DESC LIMIT 1;
   IF tid IS NULL THEN
     SELECT id INTO validation_id FROM mcq.validation_reports WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 1;
     IF NOT EXISTS(SELECT 1 FROM mcq.question_releases WHERE version_id=target) THEN
       INSERT INTO mcq.question_releases(version_id,automatic_validation_id,state,reason) VALUES(target,validation_id,'approved','Automatically checked private practice');
     END IF;
     INSERT INTO mcq.assessments(owner_id,title,kind,mode,randomize_options) VALUES(account,'Personal practice','practice','fixed',true) RETURNING id INTO aid;
     INSERT INTO mcq.assessment_questions(assessment_id,owner_id,position,version_id,points) VALUES(aid,account,1,target,1);
     UPDATE mcq.assessments SET state='published',published_at=clock_timestamp() WHERE id=aid;
     SELECT * INTO a FROM mcq.assessments WHERE id=aid;
   END IF;
 ELSIF op='start' THEN
   SELECT * INTO a FROM mcq.assessments WHERE id=target AND kind='classroom';
   IF a.id IS NULL THEN RAISE EXCEPTION 'ATTEMPT_UNAVAILABLE'; END IF;
   PERFORM pg_advisory_xact_lock(hashtextextended(a.owner_id::text,10));
   SELECT * INTO a FROM mcq.assessments WHERE id=target FOR UPDATE;
   SELECT id INTO tid FROM mcq.attempts WHERE assessment_id=target AND student_id=account AND state='in_progress' ORDER BY started_at DESC LIMIT 1;
   IF tid IS NULL THEN
     IF NOT EXISTS(SELECT 1 FROM mcq.assessment_admissions j WHERE j.assessment_id=target AND j.student_id=account AND mcq.assessment_access(account,target,j.code_id)) THEN RAISE EXCEPTION 'ATTEMPT_UNAVAILABLE'; END IF;
     aid:=target;
   END IF;
 ELSIF op IN ('save','submit') THEN
   SELECT owner_id INTO owner_id_value FROM mcq.attempts WHERE id=target AND student_id=account;
   IF owner_id_value IS NULL THEN RAISE EXCEPTION 'ATTEMPT_NOT_FOUND'; END IF;
   PERFORM pg_advisory_xact_lock(hashtextextended(owner_id_value::text,10));
   SELECT * INTO t FROM mcq.attempts WHERE id=target AND student_id=account FOR UPDATE;
   SELECT * INTO s FROM mcq.attempt_sessions WHERE attempt_id=target;
   IF s.attempt_id IS NULL THEN RAISE EXCEPTION 'ATTEMPT_NOT_FOUND'; END IF;
   tid:=target;
   IF t.state='in_progress' AND s.deadline IS NOT NULL AND clock_timestamp()>=s.deadline THEN
     PERFORM mcq.finish_attempt(tid,true);
   ELSIF t.state='in_progress' THEN
     IF s.revision IS DISTINCT FROM (body->>'revision')::integer THEN RAISE EXCEPTION 'ATTEMPT_STALE'; END IF;
     IF op='save' THEN
       IF jsonb_typeof(body->'answers') IS DISTINCT FROM 'array' OR jsonb_array_length(body->'answers') NOT BETWEEN 1 AND 50 THEN RAISE EXCEPTION 'ATTEMPT_INVALID'; END IF;
       FOR choice IN SELECT value FROM jsonb_array_elements(body->'answers') LOOP
         SELECT * INTO item FROM mcq.attempt_items WHERE attempt_id=tid AND position=(choice->>'position')::integer;
         IF item.attempt_id IS NULL OR (choice->>'selected_option')::integer NOT BETWEEN 0 AND 3 THEN RAISE EXCEPTION 'ATTEMPT_INVALID'; END IF;
         INSERT INTO mcq.answers(attempt_id,version_id,selected_option,flagged)
         VALUES(tid,item.version_id,CASE WHEN choice->>'selected_option' IS NULL THEN NULL ELSE item.option_order[(choice->>'selected_option')::integer+1] END,COALESCE((choice->>'flagged')::boolean,false))
         ON CONFLICT(attempt_id,version_id) DO UPDATE SET selected_option=EXCLUDED.selected_option,flagged=EXCLUDED.flagged,answered_at=clock_timestamp();
       END LOOP;
       UPDATE mcq.attempt_sessions SET revision=revision+1 WHERE attempt_id=tid;
     ELSE PERFORM mcq.finish_attempt(tid,false);
     END IF;
   ELSIF op='save' THEN RAISE EXCEPTION 'ATTEMPT_FINISHED';
   END IF;
 ELSE RAISE EXCEPTION 'ATTEMPT_INVALID';
 END IF;
 IF op IN ('start','practice') AND tid IS NULL THEN
   SELECT COALESCE(max(attempt_number),0)+1 INTO n FROM mcq.attempts WHERE assessment_id=aid AND student_id=account;
   stamp:=clock_timestamp();
   INSERT INTO mcq.attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key,started_at)
     VALUES(aid,a.owner_id,account,n,retry_key,stamp) RETURNING id INTO tid;
   INSERT INTO mcq.attempt_sessions(attempt_id,deadline) VALUES(tid,CASE WHEN a.time_limit_seconds IS NOT NULL THEN stamp+make_interval(secs=>a.time_limit_seconds) END);
   INSERT INTO mcq.attempt_items(attempt_id,assessment_id,owner_id,position,version_id,points,option_order)
     SELECT tid,aid,a.owner_id,row_number() OVER(ORDER BY sort_value,position),version_id,points,
       CASE WHEN a.randomize_options THEN ARRAY(SELECT x::smallint FROM generate_series(0,3) x ORDER BY random()+aq.position*0) ELSE ARRAY[0,1,2,3]::smallint[] END
     FROM (SELECT aq.*,CASE WHEN a.randomize_questions THEN random() ELSE 0 END AS sort_value FROM mcq.assessment_questions aq WHERE assessment_id=aid) aq;
   INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'attempt.started','attempt',tid);
 END IF;
 INSERT INTO mcq.attempt_commands(student_id,idempotency_key,target_id,operation,request,attempt_id) VALUES(account,retry_key,target,op,body,tid);
 RETURN jsonb_build_object('attempt_id',tid);
EXCEPTION WHEN raise_exception THEN
 IF SQLERRM IN ('ATTEMPT_FORBIDDEN','ATTEMPT_KEY_CONFLICT','ATTEMPT_UNAVAILABLE','ATTEMPT_NOT_FOUND','ATTEMPT_STALE','ATTEMPT_INVALID','ATTEMPT_FINISHED','PRACTICE_BLOCKED') THEN RETURN jsonb_build_object('error',SQLERRM); END IF;
 RAISE;
 WHEN check_violation THEN RETURN jsonb_build_object('error','ATTEMPT_UNAVAILABLE');
END $$;
REVOKE ALL ON FUNCTION mcq.attempt_action(uuid,uuid,uuid,text,jsonb) FROM PUBLIC;

CREATE FUNCTION mcq.attempt_view(account uuid,target uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE t mcq.attempts; a mcq.assessments; s mcq.attempt_sessions; released boolean; items jsonb; result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(account::text,14));
 SELECT * INTO t FROM mcq.attempts WHERE id=target AND student_id=account;
 IF t.id IS NULL OR NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='student') THEN RETURN jsonb_build_object('error','ATTEMPT_NOT_FOUND'); END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(t.owner_id::text,10));
 SELECT * INTO t FROM mcq.attempts WHERE id=target FOR UPDATE;
 SELECT * INTO s FROM mcq.attempt_sessions WHERE attempt_id=target;
 IF s.attempt_id IS NULL THEN RETURN jsonb_build_object('error','ATTEMPT_NOT_FOUND'); END IF;
 IF t.state='in_progress' AND s.deadline IS NOT NULL AND clock_timestamp()>=s.deadline THEN
   PERFORM mcq.finish_attempt(target,true);
   SELECT * INTO t FROM mcq.attempts WHERE id=target;
   SELECT * INTO s FROM mcq.attempt_sessions WHERE attempt_id=target;
 END IF;
 SELECT * INTO a FROM mcq.assessments WHERE id=t.assessment_id;
 released:=t.state<>'in_progress' AND (a.release_policy='after_submit' OR a.state='closed');
 SELECT jsonb_agg(jsonb_build_object('position',i.position,'version_id',i.version_id,'stem',v.stem,
   'options',(SELECT jsonb_agg(o.content ORDER BY ord.n) FROM unnest(i.option_order) WITH ORDINALITY ord(value,n) JOIN mcq.options o ON o.version_id=v.id AND o.ordinal=ord.value),
   'selected_option',array_position(i.option_order,ans.selected_option)-1,'flagged',COALESCE(ans.flagged,false),
   'under_review',r.state IS DISTINCT FROM 'approved') ||
   CASE WHEN released AND r.state='approved' THEN jsonb_build_object('correct_option',array_position(i.option_order,v.correct_option::smallint)-1,
     'explanation',v.explanation,'is_correct',ans.is_correct,
     'source_quotes',(SELECT jsonb_agg(evidence_quote) FROM mcq.question_sources WHERE version_id=v.id)) ELSE '{}'::jsonb END
   ORDER BY i.position) INTO items
 FROM mcq.attempt_items i JOIN mcq.question_versions v ON v.id=i.version_id LEFT JOIN mcq.answers ans ON ans.attempt_id=target AND ans.version_id=v.id
 LEFT JOIN mcq.question_releases r ON r.version_id=v.id WHERE i.attempt_id=target;
 IF released THEN SELECT jsonb_build_object('awarded_points',awarded_points,'possible_points',possible_points,'item_count',item_count) INTO result FROM mcq.attempt_scores WHERE attempt_id=target; END IF;
 RETURN jsonb_build_object('id',t.id,'assessment_id',a.id,'title',a.title,'kind',a.kind,'state',t.state,'revision',s.revision,
   'deadline',s.deadline,'server_now',clock_timestamp(),'started_at',t.started_at,'submitted_at',t.submitted_at,
   'release_policy',a.release_policy,'results_released',released,'items',items,'result',result);
END $$;
REVOKE ALL ON FUNCTION mcq.attempt_view(uuid,uuid) FROM PUBLIC;

-- Definer callees cannot resolve attacker-created temporary objects ahead of mcq.
ALTER FUNCTION mcq.guard_attempt() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.check_attempt_item() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.guard_answer() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.check_mastery_evidence() SET search_path=pg_catalog,mcq,pg_temp;
