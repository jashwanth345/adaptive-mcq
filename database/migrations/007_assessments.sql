ALTER TABLE mcq.assessments ADD COLUMN revision integer NOT NULL DEFAULT 1 CHECK(revision>0);
CREATE TABLE mcq.assessment_operations (
    owner_id uuid NOT NULL REFERENCES mcq.users,
    idempotency_key uuid NOT NULL,
    assessment_id uuid NOT NULL REFERENCES mcq.assessments,
    operation text NOT NULL,
    request jsonb NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(owner_id,idempotency_key)
);
CREATE TRIGGER immutable_assessment_operation BEFORE UPDATE OR DELETE ON mcq.assessment_operations
    FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
CREATE TABLE mcq.assessment_participants (
    assessment_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    student_id uuid NOT NULL REFERENCES mcq.users,
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY(assessment_id,student_id),
    FOREIGN KEY(assessment_id,owner_id) REFERENCES mcq.assessments(id,owner_id)
);
CREATE TABLE mcq.assessment_admissions (
    assessment_id uuid NOT NULL REFERENCES mcq.assessments,
    student_id uuid NOT NULL REFERENCES mcq.users,
    code_id uuid NOT NULL REFERENCES mcq.reference_codes,
    joined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(assessment_id,student_id),
    FOREIGN KEY(assessment_id,student_id) REFERENCES mcq.assessment_participants(assessment_id,student_id)
);
CREATE TABLE mcq.code_join_limits (
    student_id uuid PRIMARY KEY REFERENCES mcq.users,
    window_started timestamptz NOT NULL,
    requests integer NOT NULL CHECK(requests>0)
);
REVOKE ALL ON mcq.assessment_operations,mcq.assessment_participants,mcq.assessment_admissions,mcq.code_join_limits FROM PUBLIC;

CREATE FUNCTION mcq.assessment_ready(target uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE a mcq.assessments; item record;
BEGIN
    SELECT * INTO a FROM mcq.assessments WHERE id=target;
    IF a.id IS NULL THEN RETURN false; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(a.owner_id::text,10));
    PERFORM 1 FROM mcq.assessments WHERE id=target FOR SHARE;
    IF NOT EXISTS(SELECT 1 FROM mcq.assessment_questions WHERE assessment_id=target)
       OR EXISTS(SELECT 1 FROM mcq.assessment_questions aq LEFT JOIN mcq.question_releases r USING(version_id)
           WHERE aq.assessment_id=target AND (r.state IS DISTINCT FROM 'approved' OR r.reviewed_by IS DISTINCT FROM a.owner_id)) THEN RETURN false; END IF;
    FOR item IN SELECT version_id FROM mcq.assessment_questions WHERE assessment_id=target ORDER BY position LOOP
        PERFORM mcq.assert_validation_ready(item.version_id,a.owner_id);
        PERFORM mcq.assert_teacher_release_current(item.version_id);
    END LOOP;
    RETURN true;
EXCEPTION WHEN check_violation THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION mcq.assessment_ready(uuid) FROM PUBLIC;

CREATE FUNCTION mcq.assessment_action(account uuid,target uuid,retry_key uuid,op text,body jsonb,code_hash text DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE a mcq.assessments; prior mcq.assessment_operations; aid uuid; cid uuid; sid uuid; result jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(account::text,10));
    IF NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='teacher') THEN RAISE EXCEPTION 'ASSESSMENT_FORBIDDEN'; END IF;
    SELECT * INTO prior FROM mcq.assessment_operations WHERE owner_id=account AND idempotency_key=retry_key;
    IF prior.assessment_id IS NOT NULL THEN
        IF prior.operation<>op OR prior.request<>body OR (op<>'create' AND prior.assessment_id IS DISTINCT FROM target) THEN RAISE EXCEPTION 'ASSESSMENT_KEY_CONFLICT'; END IF;
        IF prior.result ? 'code_id' AND NOT EXISTS(SELECT 1 FROM mcq.reference_codes WHERE id=(prior.result->>'code_id')::uuid AND code_digest=code_hash) THEN RAISE EXCEPTION 'CODE_COLLISION'; END IF;
        RETURN prior.result;
    END IF;
    IF op='create' THEN
        IF NOT EXISTS(SELECT 1 FROM mcq.courses WHERE id=(body->>'course_id')::uuid AND owner_id=account) THEN RAISE EXCEPTION 'ASSESSMENT_NOT_FOUND'; END IF;
        INSERT INTO mcq.assessments(owner_id,course_id,title,kind,mode) VALUES(account,(body->>'course_id')::uuid,body->>'title','classroom','fixed') RETURNING id INTO aid;
    ELSE
        SELECT * INTO a FROM mcq.assessments WHERE id=target AND owner_id=account AND kind='classroom' FOR UPDATE;
        IF a.id IS NULL THEN RAISE EXCEPTION 'ASSESSMENT_NOT_FOUND'; END IF;
        aid:=a.id;
    END IF;
    IF op IN ('create','save') THEN
        IF op='save' AND (a.state<>'draft' OR a.revision IS DISTINCT FROM (body->>'revision')::integer) THEN RAISE EXCEPTION 'ASSESSMENT_STALE'; END IF;
        IF jsonb_array_length(body->'version_ids')>50 OR jsonb_array_length(body->'version_ids')<1 THEN RAISE EXCEPTION 'ASSESSMENT_INVALID'; END IF;
        IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(body->'version_ids') x WHERE NOT EXISTS(
            SELECT 1 FROM mcq.question_versions v JOIN mcq.questions q ON q.id=v.question_id
            WHERE v.id=x.value::uuid AND v.owner_id=account AND NOT q.archived
            AND NOT EXISTS(SELECT 1 FROM mcq.question_versions newer WHERE newer.question_id=v.question_id AND newer.version>v.version))) THEN RAISE EXCEPTION 'ASSESSMENT_QUESTION_UNAVAILABLE'; END IF;
        UPDATE mcq.assessments SET title=body->>'title',time_limit_seconds=(body->>'time_limit_seconds')::integer,
            max_attempts=(body->>'max_attempts')::integer,randomize_questions=(body->>'randomize_questions')::boolean,
            randomize_options=(body->>'randomize_options')::boolean,release_policy=body->>'release_policy',
            revision=CASE WHEN op='save' THEN revision+1 ELSE revision END WHERE id=aid;
        DELETE FROM mcq.assessment_questions WHERE assessment_id=aid;
        INSERT INTO mcq.assessment_questions(assessment_id,owner_id,position,version_id,points)
            SELECT aid,account,ordinality,value::uuid,1 FROM jsonb_array_elements_text(body->'version_ids') WITH ORDINALITY;
    ELSIF op='publish' THEN
        IF a.state<>'draft' OR a.revision IS DISTINCT FROM (body->>'revision')::integer THEN RAISE EXCEPTION 'ASSESSMENT_STALE'; END IF;
        IF NOT mcq.assessment_ready(aid) THEN RAISE EXCEPTION 'ASSESSMENT_BLOCKED'; END IF;
        UPDATE mcq.assessments SET state='published',published_at=clock_timestamp() WHERE id=aid;
    ELSIF op IN ('rotate','revoke','close') THEN
        IF a.state<>'published' THEN RAISE EXCEPTION 'ASSESSMENT_STALE'; END IF;
        IF op='rotate' AND NOT mcq.assessment_ready(aid) THEN RAISE EXCEPTION 'ASSESSMENT_BLOCKED'; END IF;
        UPDATE mcq.reference_codes SET revoked_at=clock_timestamp() WHERE assessment_id=aid AND revoked_at IS NULL;
        IF op='close' THEN UPDATE mcq.assessments SET state='closed' WHERE id=aid; END IF;
    ELSIF op='participant' THEN
        IF a.state='closed' THEN RAISE EXCEPTION 'ASSESSMENT_STALE'; END IF;
        SELECT u.id INTO sid FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id
            WHERE u.email=body->>'email' AND u.active AND r.role='student';
        IF sid IS NULL THEN RAISE EXCEPTION 'PARTICIPANT_UNAVAILABLE'; END IF;
        IF NOT EXISTS(SELECT 1 FROM mcq.assessment_participants WHERE assessment_id=aid AND student_id=sid)
           AND (SELECT count(*) FROM mcq.assessment_participants WHERE assessment_id=aid)>=200 THEN RAISE EXCEPTION 'PARTICIPANT_LIMIT'; END IF;
        INSERT INTO mcq.assessment_participants(assessment_id,owner_id,student_id,active) VALUES(aid,account,sid,(body->>'active')::boolean)
            ON CONFLICT(assessment_id,student_id) DO UPDATE SET active=EXCLUDED.active;
    ELSE RAISE EXCEPTION 'ASSESSMENT_INVALID';
    END IF;
    result:=jsonb_build_object('assessment_id',aid);
    IF op IN ('publish','rotate') THEN
        IF body->>'expiry_hours' IS NULL OR (body->>'expiry_hours')::integer NOT BETWEEN 1 AND 720 OR code_hash IS NULL THEN RAISE EXCEPTION 'ASSESSMENT_INVALID'; END IF;
        INSERT INTO mcq.reference_codes(assessment_id,code_digest,expires_at) VALUES(aid,code_hash,clock_timestamp()+make_interval(hours=>(body->>'expiry_hours')::integer)) RETURNING id INTO cid;
        result:=result||jsonb_build_object('code_id',cid);
    END IF;
    INSERT INTO mcq.assessment_operations(owner_id,idempotency_key,assessment_id,operation,request,result) VALUES(account,retry_key,aid,op,body,result);
    INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'assessment.'||op,'assessment',aid);
    RETURN result;
EXCEPTION
    WHEN raise_exception THEN
        IF SQLERRM IN ('ASSESSMENT_FORBIDDEN','ASSESSMENT_KEY_CONFLICT','ASSESSMENT_NOT_FOUND','ASSESSMENT_STALE','ASSESSMENT_INVALID','ASSESSMENT_QUESTION_UNAVAILABLE','ASSESSMENT_BLOCKED','CODE_COLLISION','PARTICIPANT_UNAVAILABLE','PARTICIPANT_LIMIT') THEN RETURN jsonb_build_object('error',SQLERRM); END IF;
        RAISE;
    WHEN unique_violation THEN RETURN jsonb_build_object('error','CODE_COLLISION');
    WHEN check_violation THEN RETURN jsonb_build_object('error','ASSESSMENT_BLOCKED');
END $$;
REVOKE ALL ON FUNCTION mcq.assessment_action(uuid,uuid,uuid,text,jsonb,text) FROM PUBLIC;

CREATE FUNCTION mcq.assessment_access(account uuid,target uuid,code uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE a mcq.assessments;
BEGIN
    SELECT * INTO a FROM mcq.assessments WHERE id=target;
    IF a.id IS NULL THEN RETURN false; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(a.owner_id::text,10));
    SELECT * INTO a FROM mcq.assessments WHERE id=target FOR SHARE;
    IF a.id IS NULL OR a.state<>'published' OR a.kind<>'classroom'
       OR NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='student')
       OR NOT EXISTS(SELECT 1 FROM mcq.assessment_participants WHERE assessment_id=target AND student_id=account AND active)
       OR NOT EXISTS(SELECT 1 FROM mcq.reference_codes WHERE id=code AND assessment_id=target AND revoked_at IS NULL AND expires_at>clock_timestamp())
       OR (SELECT count(*) FROM mcq.attempts WHERE assessment_id=target AND student_id=account)>=a.max_attempts THEN RETURN false; END IF;
    RETURN mcq.assessment_ready(target);
END $$;
REVOKE ALL ON FUNCTION mcq.assessment_access(uuid,uuid,uuid) FROM PUBLIC;

CREATE FUNCTION mcq.join_assessment(account uuid,code_hash text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE c mcq.reference_codes; a mcq.assessments; n integer; existing boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(account::text,14));
    INSERT INTO mcq.code_join_limits(student_id,window_started,requests) VALUES(account,clock_timestamp(),1)
    ON CONFLICT(student_id) DO UPDATE SET
        requests=CASE WHEN mcq.code_join_limits.window_started<clock_timestamp()-interval '60 seconds' THEN 1 ELSE mcq.code_join_limits.requests+1 END,
        window_started=CASE WHEN mcq.code_join_limits.window_started<clock_timestamp()-interval '60 seconds' THEN clock_timestamp() ELSE mcq.code_join_limits.window_started END
        RETURNING requests INTO n;
    IF n>10 THEN RETURN jsonb_build_object('error','CODE_RATE_LIMIT'); END IF;
    SELECT * INTO c FROM mcq.reference_codes WHERE code_digest=code_hash;
    IF c.id IS NULL THEN RETURN jsonb_build_object('error','ASSESSMENT_UNAVAILABLE'); END IF;
    SELECT * INTO a FROM mcq.assessments WHERE id=c.assessment_id;
    PERFORM pg_advisory_xact_lock(hashtextextended(a.owner_id::text,10));
    PERFORM 1 FROM mcq.assessments WHERE id=a.id FOR SHARE;
    IF NOT mcq.assessment_access(account,a.id,c.id) THEN RETURN jsonb_build_object('error','ASSESSMENT_UNAVAILABLE'); END IF;
    SELECT EXISTS(SELECT 1 FROM mcq.assessment_admissions WHERE assessment_id=a.id AND student_id=account AND code_id=c.id) INTO existing;
    INSERT INTO mcq.assessment_admissions(assessment_id,student_id,code_id) VALUES(a.id,account,c.id)
        ON CONFLICT(assessment_id,student_id) DO UPDATE SET code_id=EXCLUDED.code_id;
    INSERT INTO mcq.course_memberships(course_id,student_id) VALUES(a.course_id,account)
        ON CONFLICT(course_id,student_id) DO UPDATE SET active=true;
    IF NOT existing THEN INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'assessment.joined','assessment',a.id); END IF;
    RETURN jsonb_build_object('assessment_id',a.id);
END $$;
REVOKE ALL ON FUNCTION mcq.join_assessment(uuid,text) FROM PUBLIC;

CREATE FUNCTION mcq.managed_attempt_access() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE admission mcq.assessment_admissions;
BEGIN
    IF EXISTS(SELECT 1 FROM mcq.assessment_operations WHERE assessment_id=NEW.assessment_id AND operation='publish') THEN
        SELECT * INTO admission FROM mcq.assessment_admissions WHERE assessment_id=NEW.assessment_id AND student_id=NEW.student_id;
        IF admission.code_id IS NULL OR NOT mcq.assessment_access(NEW.student_id,NEW.assessment_id,admission.code_id) THEN
            RAISE EXCEPTION 'A current authorized code admission is required' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
-- PostgreSQL runs same-kind triggers in name order. Take the owner lock before
-- the legacy attempt_gate takes the assessment row lock, matching publication.
CREATE TRIGGER a_managed_attempt_access BEFORE INSERT ON mcq.attempts FOR EACH ROW EXECUTE FUNCTION mcq.managed_attempt_access();
REVOKE ALL ON FUNCTION mcq.managed_attempt_access() FROM PUBLIC;
-- Harden callees reached through the trusted publication boundary.
ALTER FUNCTION mcq.guard_assessment() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.guard_assessment_items() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.check_code() SET search_path=pg_catalog,mcq,pg_temp;
