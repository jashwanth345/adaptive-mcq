ALTER TABLE mcq.feedback DROP CONSTRAINT feedback_category_check;
ALTER TABLE mcq.feedback ADD CHECK(category IN ('wrong_answer','wrong_explanation','ambiguous','poor_wording',
 'weak_distractor','too_easy','too_difficult','duplicate','not_from_material','mathematical_error','other','rating'));
ALTER TABLE mcq.feedback ADD COLUMN rating text;
ALTER TABLE mcq.feedback ADD CHECK((category='rating' AND rating IS NOT NULL AND rating IN ('helpful','poor')) OR (category<>'rating' AND rating IS NULL));
CREATE INDEX feedback_reporter_version ON mcq.feedback(student_id,version_id,category);
CREATE TABLE mcq.feedback_cases(
 version_id uuid PRIMARY KEY REFERENCES mcq.question_versions,
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0),
 state text NOT NULL DEFAULT 'open' CHECK(state IN ('open','reviewing','resolved','dismissed')),
 confirmed_defect boolean NOT NULL DEFAULT false,
 grade_review text NOT NULL DEFAULT 'not_required' CHECK(grade_review IN ('not_required','pending','acknowledged')),
 updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO mcq.feedback_cases(version_id) SELECT DISTINCT version_id FROM mcq.feedback;
CREATE TABLE mcq.feedback_commands(
 actor_id uuid NOT NULL REFERENCES mcq.users, idempotency_key uuid NOT NULL,
 target_id uuid NOT NULL, operation text NOT NULL, request jsonb NOT NULL, result jsonb NOT NULL,
 PRIMARY KEY(actor_id,idempotency_key)
);
CREATE TABLE mcq.feedback_decisions(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), version_id uuid NOT NULL REFERENCES mcq.feedback_cases,
 actor_id uuid NOT NULL REFERENCES mcq.users, action text NOT NULL,
 note text NOT NULL CHECK(length(btrim(note)) BETWEEN 3 AND 600), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER preserve_feedback_command BEFORE UPDATE OR DELETE ON mcq.feedback_commands FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
CREATE TRIGGER preserve_feedback_decision BEFORE UPDATE OR DELETE ON mcq.feedback_decisions FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
-- A confirmed defect requires a new version, even if fresh reports pass for the old one.
CREATE FUNCTION mcq.feedback_release_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,mcq,pg_temp AS $$
BEGIN
 IF NEW.state='approved' AND EXISTS(SELECT 1 FROM mcq.feedback_cases WHERE version_id=NEW.version_id AND confirmed_defect) THEN
  RAISE EXCEPTION 'Confirmed defect requires a corrected version' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER feedback_release_guard BEFORE INSERT OR UPDATE ON mcq.question_releases FOR EACH ROW EXECUTE FUNCTION mcq.feedback_release_guard();

CREATE FUNCTION mcq.feedback_late_completion() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,mcq,pg_temp AS $$
BEGIN
 IF OLD.state='in_progress' AND NEW.state IN ('submitted','expired') THEN
  UPDATE mcq.feedback_cases SET grade_review='pending',revision=revision+1,updated_at=clock_timestamp()
  WHERE confirmed_defect AND version_id IN (SELECT version_id FROM mcq.attempt_items WHERE attempt_id=NEW.id);
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER feedback_late_completion AFTER UPDATE ON mcq.attempts FOR EACH ROW EXECUTE FUNCTION mcq.feedback_late_completion();

CREATE FUNCTION mcq.feedback_can_review(account uuid,target uuid) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM mcq.question_versions q JOIN mcq.users u ON u.id=q.owner_id
  WHERE q.id=target AND q.owner_id=account AND u.active AND (
   EXISTS(SELECT 1 FROM mcq.user_roles WHERE user_id=account AND role='teacher') OR (
    EXISTS(SELECT 1 FROM mcq.user_roles WHERE user_id=account AND role='student') AND NOT EXISTS(
     SELECT 1 FROM mcq.assessment_questions aq JOIN mcq.assessments a ON a.id=aq.assessment_id
      WHERE aq.version_id=target AND a.kind='classroom'))));
$$;
REVOKE ALL ON FUNCTION mcq.feedback_can_review(uuid,uuid) FROM PUBLIC;

CREATE FUNCTION mcq.feedback_action(account uuid,target uuid,retry_key uuid,op text,body jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE old mcq.feedback_commands; q mcq.question_versions; a mcq.attempts; c mcq.feedback_cases;
 report_id uuid; result jsonb; new_state text; category_value text;
BEGIN
 -- Same lock order as attempts: reporter first, then owner. Reviews only need owner.
 IF op='report' THEN PERFORM pg_advisory_xact_lock(hashtextextended(account::text,14)); END IF;
 IF NOT EXISTS(SELECT 1 FROM mcq.users WHERE id=account AND active) THEN RAISE EXCEPTION 'FEEDBACK_FORBIDDEN'; END IF;
 IF op='report' THEN
  SELECT * INTO a FROM mcq.attempts WHERE id=target AND student_id=account AND state IN ('submitted','expired');
  SELECT v.* INTO q FROM mcq.attempt_items i JOIN mcq.question_versions v ON v.id=i.version_id
    WHERE i.attempt_id=a.id AND i.version_id=(body->>'version_id')::uuid;
  IF q.id IS NULL OR NOT EXISTS(SELECT 1 FROM mcq.user_roles WHERE user_id=account AND role='student') THEN RAISE EXCEPTION 'FEEDBACK_NOT_FOUND'; END IF;
 ELSE
  SELECT * INTO q FROM mcq.question_versions WHERE id=target AND owner_id=account;
  IF q.id IS NULL OR NOT mcq.feedback_can_review(account,target) THEN RAISE EXCEPTION 'FEEDBACK_NOT_FOUND'; END IF;
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(q.owner_id::text,10));
 SELECT * INTO old FROM mcq.feedback_commands WHERE actor_id=account AND idempotency_key=retry_key;
 IF old.actor_id IS NOT NULL THEN
  IF old.target_id<>target OR old.operation<>op OR old.request<>body THEN RAISE EXCEPTION 'FEEDBACK_KEY_CONFLICT'; END IF;
  RETURN old.result;
 END IF;
 IF op='report' THEN
  category_value:=body->>'category';
  IF category_value IS NULL OR category_value NOT IN ('wrong_answer','wrong_explanation','ambiguous','poor_wording','weak_distractor','too_easy','too_difficult','duplicate','not_from_material','mathematical_error','other','rating')
   OR length(COALESCE(body->>'comment',''))>2000 OR (category_value='rating' AND COALESCE(body->>'rating','') NOT IN ('helpful','poor'))
   OR (category_value<>'rating' AND body->>'rating' IS NOT NULL) THEN RAISE EXCEPTION 'FEEDBACK_INVALID'; END IF;
  SELECT id INTO report_id FROM mcq.feedback WHERE student_id=account AND version_id=q.id AND category=category_value ORDER BY created_at,id LIMIT 1;
  IF report_id IS NULL THEN
   INSERT INTO mcq.feedback(attempt_id,version_id,student_id,category,rating,comment) VALUES(a.id,q.id,account,category_value,body->>'rating',NULLIF(btrim(body->>'comment'),'')) RETURNING id INTO report_id;
   INSERT INTO mcq.feedback_cases(version_id) VALUES(q.id) ON CONFLICT(version_id) DO UPDATE
    SET revision=mcq.feedback_cases.revision+1,updated_at=clock_timestamp(),state=CASE WHEN mcq.feedback_cases.confirmed_defect THEN 'resolved' ELSE 'open' END;
   UPDATE mcq.feedback SET state='resolved' WHERE id=report_id AND EXISTS(SELECT 1 FROM mcq.feedback_cases WHERE version_id=q.id AND confirmed_defect);
   INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'feedback.reported','feedback',report_id);
   result:=jsonb_build_object('report_id',report_id,'duplicate',false);
  ELSE result:=jsonb_build_object('report_id',report_id,'duplicate',true);
  END IF;
 ELSE
  SELECT * INTO c FROM mcq.feedback_cases WHERE version_id=q.id FOR UPDATE;
  IF c.version_id IS NULL THEN RAISE EXCEPTION 'FEEDBACK_NOT_FOUND'; END IF;
  IF c.revision IS DISTINCT FROM (body->>'revision')::integer THEN RAISE EXCEPTION 'FEEDBACK_STALE'; END IF;
  IF length(btrim(COALESCE(body->>'note',''))) NOT BETWEEN 3 AND 600 OR op NOT IN ('review','dismiss','confirm_defect','acknowledge_grades') THEN RAISE EXCEPTION 'FEEDBACK_INVALID'; END IF;
  IF c.confirmed_defect AND op<>'acknowledge_grades' THEN RAISE EXCEPTION 'FEEDBACK_CONFIRMED'; END IF;
  IF op='acknowledge_grades' THEN
   IF c.grade_review<>'pending' THEN RAISE EXCEPTION 'FEEDBACK_INVALID'; END IF;
   UPDATE mcq.feedback_cases SET grade_review='acknowledged' WHERE version_id=q.id;
  ELSE
   new_state:=CASE op WHEN 'review' THEN 'reviewing' WHEN 'dismiss' THEN 'dismissed' ELSE 'resolved' END;
   UPDATE mcq.feedback_cases SET state=new_state,confirmed_defect=(op='confirm_defect'),
    grade_review=CASE WHEN op='confirm_defect' THEN 'pending' ELSE grade_review END WHERE version_id=q.id;
   UPDATE mcq.feedback SET state=new_state WHERE version_id=q.id AND state IN ('open','reviewing');
   IF op='confirm_defect' THEN
    UPDATE mcq.question_releases SET state='quarantined',reason='Confirmed feedback defect: '||(body->>'note') WHERE version_id=q.id;
   END IF;
  END IF;
  UPDATE mcq.feedback_cases SET revision=revision+1,updated_at=clock_timestamp() WHERE version_id=q.id;
  INSERT INTO mcq.feedback_decisions(version_id,actor_id,action,note) VALUES(q.id,account,op,body->>'note');
  INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'feedback.'||op,'question_version',q.id);
  result:=jsonb_build_object('version_id',q.id);
 END IF;
 INSERT INTO mcq.feedback_commands VALUES(account,retry_key,target,op,body,result);
 RETURN result;
EXCEPTION WHEN raise_exception THEN
 IF SQLERRM IN ('FEEDBACK_FORBIDDEN','FEEDBACK_NOT_FOUND','FEEDBACK_KEY_CONFLICT','FEEDBACK_INVALID','FEEDBACK_STALE','FEEDBACK_CONFIRMED') THEN RETURN jsonb_build_object('error',SQLERRM); END IF;
 RAISE;
END $$;

CREATE FUNCTION mcq.feedback_history(account uuid,start_at integer,page_size integer) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
 SELECT jsonb_build_object('total',(SELECT count(*) FROM mcq.feedback WHERE student_id=account),'items',COALESCE((
  SELECT jsonb_agg(x) FROM (SELECT f.id,f.version_id,f.attempt_id,f.category,f.rating,f.comment,f.state,f.created_at,v.stem,v.version
   FROM mcq.feedback f JOIN mcq.question_versions v ON v.id=f.version_id WHERE f.student_id=account
   ORDER BY f.created_at DESC,f.id LIMIT greatest(1,least(page_size,50)) OFFSET greatest(0,start_at)) x),'[]'::jsonb));
$$;
CREATE FUNCTION mcq.feedback_case_summary(target uuid) RETURNS jsonb
LANGUAGE sql SET search_path=pg_catalog,mcq,pg_temp AS $$
 SELECT jsonb_build_object('version_id',q.id,'version',q.version,'stem',q.stem,'state',c.state,'revision',c.revision,
  'confirmed_defect',c.confirmed_defect,'grade_review',c.grade_review,'updated_at',c.updated_at,
  'exposures',(SELECT count(DISTINCT a.student_id) FROM mcq.attempt_items i JOIN mcq.attempts a ON a.id=i.attempt_id WHERE i.version_id=q.id),
  'reporters',(SELECT count(DISTINCT student_id) FROM mcq.feedback WHERE version_id=q.id AND (category<>'rating' OR rating='poor')),
  'open_reporters',(SELECT count(DISTINCT student_id) FROM mcq.feedback WHERE version_id=q.id AND state IN ('open','reviewing') AND (category<>'rating' OR rating='poor')),
  'helpful',(SELECT count(DISTINCT student_id) FROM mcq.feedback WHERE version_id=q.id AND rating='helpful'),
  'poor',(SELECT count(DISTINCT student_id) FROM mcq.feedback WHERE version_id=q.id AND rating='poor'),
  'completed_attempts',(SELECT count(*) FROM mcq.attempt_items i JOIN mcq.attempts a ON a.id=i.attempt_id WHERE i.version_id=q.id AND a.state IN ('submitted','expired')),
  'release_state',(SELECT state FROM mcq.question_releases WHERE version_id=q.id))
 FROM mcq.feedback_cases c JOIN mcq.question_versions q ON q.id=c.version_id WHERE q.id=target;
$$;
CREATE FUNCTION mcq.feedback_queue(account uuid,start_at integer,page_size integer) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
 SELECT jsonb_build_object('total',(SELECT count(*) FROM mcq.feedback_cases c JOIN mcq.question_versions q ON q.id=c.version_id WHERE q.owner_id=account AND mcq.feedback_can_review(account,q.id)),
 'items',COALESCE((SELECT jsonb_agg(mcq.feedback_case_summary(x.version_id)) FROM (
  SELECT c.version_id FROM mcq.feedback_cases c JOIN mcq.question_versions q ON q.id=c.version_id WHERE q.owner_id=account AND mcq.feedback_can_review(account,q.id)
  ORDER BY (c.grade_review='pending') DESC,(c.state IN ('open','reviewing')) DESC,c.updated_at DESC,c.version_id
  LIMIT greatest(1,least(page_size,50)) OFFSET greatest(0,start_at)) x),'[]'::jsonb));
$$;
CREATE FUNCTION mcq.feedback_detail(account uuid,target uuid,start_at integer,page_size integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE summary jsonb; reports jsonb; events jsonb;
BEGIN
 IF NOT mcq.feedback_can_review(account,target) THEN RETURN jsonb_build_object('error','FEEDBACK_NOT_FOUND'); END IF;
 summary:=mcq.feedback_case_summary(target);
 IF summary IS NULL THEN RETURN jsonb_build_object('error','FEEDBACK_NOT_FOUND'); END IF;
 SELECT COALESCE(jsonb_agg(x),'[]'::jsonb) INTO reports FROM (
  SELECT id,category,rating,comment,state,created_at FROM mcq.feedback WHERE version_id=target ORDER BY created_at DESC,id
   LIMIT greatest(1,least(page_size,50)) OFFSET greatest(0,start_at)) x;
 SELECT COALESCE(jsonb_agg(x),'[]'::jsonb) INTO events FROM (
  SELECT action,note,created_at FROM mcq.feedback_decisions WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 20) x;
 RETURN jsonb_build_object('summary',summary,'reports',reports,'total_reports',(SELECT count(*) FROM mcq.feedback WHERE version_id=target),'decisions',events);
END $$;
REVOKE ALL ON mcq.feedback_cases,mcq.feedback_commands,mcq.feedback_decisions FROM PUBLIC;
REVOKE ALL ON FUNCTION mcq.feedback_action(uuid,uuid,uuid,text,jsonb),mcq.feedback_history(uuid,integer,integer),
 mcq.feedback_case_summary(uuid),mcq.feedback_queue(uuid,integer,integer),mcq.feedback_detail(uuid,uuid,integer,integer) FROM PUBLIC;

-- Confirmed versions require correction, never reapproval in place.
CREATE OR REPLACE FUNCTION mcq.teacher_approval_ready(account uuid,target uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM mcq.question_versions WHERE id=target AND owner_id=account)
       OR (EXISTS(SELECT 1 FROM mcq.teacher_review_events WHERE version_id=target AND action='reject') OR EXISTS(SELECT 1 FROM mcq.feedback_cases WHERE version_id=target AND confirmed_defect)) THEN RETURN false; END IF;
    PERFORM mcq.assert_validation_ready(target,account);
    RETURN true;
EXCEPTION WHEN check_violation THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION mcq.teacher_approval_ready(uuid,uuid) FROM PUBLIC;


-- Confirmed versions require correction, never reapproval in place.
CREATE OR REPLACE FUNCTION mcq.teacher_review_action(account uuid,target uuid,retry_key uuid,operation text,body jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE q mcq.question_versions; previous mcq.teacher_review_events; result_version uuid; event_id uuid; validation_id uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(account::text,10));
    SELECT * INTO q FROM mcq.question_versions WHERE id=target AND owner_id=account FOR UPDATE;
    IF q.id IS NULL THEN RAISE EXCEPTION 'TEACHER_REVIEW_NOT_FOUND'; END IF;
    IF NOT EXISTS(SELECT 1 FROM mcq.users WHERE id=account AND active)
       OR NOT EXISTS(SELECT 1 FROM mcq.user_roles WHERE user_id=account AND role='teacher') THEN
        RAISE EXCEPTION 'TEACHER_REVIEW_FORBIDDEN';
    END IF;
    SELECT * INTO previous FROM mcq.teacher_review_events WHERE owner_id=account AND idempotency_key=retry_key;
    IF previous.id IS NOT NULL THEN
        IF previous.base_version_id<>target OR previous.action<>operation OR previous.request<>body THEN
            RAISE EXCEPTION 'TEACHER_REVIEW_KEY_CONFLICT';
        END IF;
        RETURN jsonb_build_object('version_id',previous.version_id);
    END IF;
    IF EXISTS(SELECT 1 FROM mcq.questions WHERE id=q.question_id AND archived)
       OR EXISTS(SELECT 1 FROM mcq.question_versions WHERE question_id=q.question_id AND version>q.version) THEN
        RAISE EXCEPTION 'TEACHER_REVIEW_STALE';
    END IF;
    IF operation NOT IN ('edit','approve','reject') OR operation IS NULL OR body IS NULL
       OR jsonb_typeof(body)<>'object' OR length(btrim(COALESCE(body->>'note','')))<3
       OR length(body->>'note')>600 THEN RAISE EXCEPTION 'TEACHER_REVIEW_INVALID'; END IF;
    result_version := target;
    IF operation='edit' THEN
        IF q.question_type<>'conceptual' OR jsonb_typeof(body->'options') IS DISTINCT FROM 'array'
           OR jsonb_array_length(body->'options')<>4 THEN RAISE EXCEPTION 'TEACHER_REVIEW_INVALID'; END IF;
        INSERT INTO mcq.question_versions(question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type)
        VALUES(q.question_id,account,q.version+1,q.topic_id,q.generation_run_id,body->>'stem',body->>'explanation',
            (body->>'correct_option')::smallint,body->>'difficulty',body->>'cognitive_level',q.question_type) RETURNING id INTO result_version;
        INSERT INTO mcq.options(version_id,ordinal,content)
            SELECT result_version,ordinality-1,value FROM jsonb_array_elements_text(body->'options') WITH ORDINALITY;
        INSERT INTO mcq.question_sources(version_id,chunk_id,owner_id,evidence_quote)
            SELECT result_version,chunk_id,owner_id,evidence_quote FROM mcq.question_sources WHERE version_id=target;
        UPDATE mcq.question_releases SET state='quarantined',reason='Superseded by teacher edit' WHERE version_id=target;
    ELSIF operation='approve' THEN
        IF (EXISTS(SELECT 1 FROM mcq.teacher_review_events WHERE version_id=target AND action='reject') OR EXISTS(SELECT 1 FROM mcq.feedback_cases WHERE version_id=target AND confirmed_defect)) THEN
            RAISE EXCEPTION 'TEACHER_REVIEW_REJECTED';
        END IF;
        BEGIN
            PERFORM mcq.assert_validation_ready(target,account);
        EXCEPTION WHEN check_violation THEN RAISE EXCEPTION 'TEACHER_APPROVAL_BLOCKED'; END;
        SELECT id INTO validation_id FROM mcq.validation_reports WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 1;
    END IF;
    INSERT INTO mcq.teacher_review_events(owner_id,base_version_id,version_id,idempotency_key,action,request,validation_report_id)
        VALUES(account,target,result_version,retry_key,operation,body,validation_id) RETURNING id INTO event_id;
    IF operation='approve' THEN
        INSERT INTO mcq.question_releases(version_id,teacher_review_id,reviewed_by,state,reason)
            VALUES(target,event_id,account,'approved',body->>'note')
            ON CONFLICT(version_id) DO UPDATE SET verification_id=NULL,teacher_review_id=event_id,
                reviewed_by=account,state='approved',reason=EXCLUDED.reason;
    ELSIF operation='reject' THEN
        UPDATE mcq.question_releases SET state='quarantined',reason=body->>'note' WHERE version_id=target;
    END IF;
    INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id)
        VALUES(account,'teacher.question_'||operation,'question_version',result_version);
    RETURN jsonb_build_object('version_id',result_version);
EXCEPTION WHEN raise_exception THEN
    -- Expected business refusals are structured results. The exception block
    -- rolls back this operation's writes before returning a safe error code.
    IF SQLERRM IN ('TEACHER_REVIEW_NOT_FOUND','TEACHER_REVIEW_FORBIDDEN','TEACHER_REVIEW_STALE',
        'TEACHER_REVIEW_KEY_CONFLICT','TEACHER_REVIEW_REJECTED','TEACHER_APPROVAL_BLOCKED','TEACHER_REVIEW_INVALID') THEN
        RETURN jsonb_build_object('error',SQLERRM);
    END IF;
    RAISE;
END $$;
REVOKE ALL ON FUNCTION mcq.teacher_review_action(uuid,uuid,uuid,text,jsonb) FROM PUBLIC;


CREATE FUNCTION mcq.feedback_confirmed(account uuid,target uuid) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM mcq.feedback_cases c JOIN mcq.question_versions q ON q.id=c.version_id
  WHERE q.id=target AND q.owner_id=account AND c.confirmed_defect);
$$;
REVOKE ALL ON FUNCTION mcq.feedback_confirmed(uuid,uuid) FROM PUBLIC;
