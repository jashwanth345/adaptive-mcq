-- Add a categorical teacher-evidence path; preserve historical score-based records.
CREATE TABLE mcq.teacher_review_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    base_version_id uuid NOT NULL,
    version_id uuid NOT NULL,
    idempotency_key uuid NOT NULL,
    action text NOT NULL CHECK(action IN ('edit','approve','reject')),
    request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'),
    validation_report_id uuid REFERENCES mcq.validation_reports,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY(base_version_id,owner_id) REFERENCES mcq.question_versions(id,owner_id),
    FOREIGN KEY(version_id,owner_id) REFERENCES mcq.question_versions(id,owner_id),
    UNIQUE(owner_id,idempotency_key), UNIQUE(id,version_id),
    CHECK((action='approve')=(validation_report_id IS NOT NULL)),
    CHECK((action='edit')=(base_version_id<>version_id))
);
CREATE INDEX teacher_review_history ON mcq.teacher_review_events(owner_id,version_id,created_at DESC,id DESC);
CREATE TRIGGER preserve_teacher_review BEFORE UPDATE OR DELETE ON mcq.teacher_review_events
    FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
REVOKE ALL ON mcq.teacher_review_events FROM PUBLIC;

ALTER TABLE mcq.question_releases ALTER COLUMN verification_id DROP NOT NULL;
ALTER TABLE mcq.question_releases ADD COLUMN teacher_review_id uuid;
ALTER TABLE mcq.question_releases ADD FOREIGN KEY(teacher_review_id,version_id)
    REFERENCES mcq.teacher_review_events(id,version_id);
ALTER TABLE mcq.question_releases ADD CHECK ((verification_id IS NULL)<>(teacher_review_id IS NULL));

CREATE OR REPLACE FUNCTION mcq.check_release() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE v question_verifications; q question_versions; e teacher_review_events; d validation_reports; ai verifier_reports;
BEGIN
    SELECT * INTO q FROM question_versions WHERE id=NEW.version_id;
    IF NEW.teacher_review_id IS NOT NULL THEN
        SELECT * INTO e FROM teacher_review_events WHERE id=NEW.teacher_review_id AND version_id=q.id;
        SELECT * INTO d FROM validation_reports WHERE id=e.validation_report_id AND version_id=q.id;
        SELECT * INTO ai FROM verifier_reports WHERE id=d.verifier_report_id AND version_id=q.id;
        IF e.id IS NULL OR e.action<>'approve' OR e.owner_id IS DISTINCT FROM NEW.reviewed_by
           OR e.owner_id IS DISTINCT FROM q.owner_id OR d.id IS NULL OR NOT d.technical_pass
           OR ai.recommendation IS DISTINCT FROM 'PASS' OR ai.mode IS DISTINCT FROM 'ollama'
           OR (ai.result->'blind_option') IS DISTINCT FROM to_jsonb(q.correct_option)
           OR (q.question_type='numerical' AND d.math_status<>'pass') THEN
            RAISE EXCEPTION 'Release requires matching teacher and technical evidence' USING ERRCODE='23514';
        END IF;
    ELSE
        SELECT * INTO v FROM question_verifications WHERE id=NEW.verification_id AND version_id=q.id;
        IF v.id IS NULL OR v.status<>'PASS' OR v.blind_option<>q.correct_option
           OR (q.question_type='numerical' AND v.math_result<>'pass') THEN
            RAISE EXCEPTION 'Release requires matching legacy verification' USING ERRCODE='23514';
        END IF;
    END IF;
    IF NOT EXISTS(SELECT 1 FROM question_sources WHERE version_id=q.id)
       OR (NEW.reviewed_by IS NOT NULL AND NEW.reviewed_by<>q.owner_id) THEN
        RAISE EXCEPTION 'Release requires owned source evidence and reviewer' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

-- New evidence paths must freeze source links too, including before approval.
CREATE OR REPLACE FUNCTION mcq.seal_sources() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
BEGIN
    PERFORM 1 FROM question_versions WHERE id=NEW.version_id FOR UPDATE;
    IF EXISTS(SELECT 1 FROM question_verifications WHERE version_id=NEW.version_id)
       OR EXISTS(SELECT 1 FROM verifier_reports WHERE version_id=NEW.version_id)
       OR EXISTS(SELECT 1 FROM validation_reports WHERE version_id=NEW.version_id) THEN
        RAISE EXCEPTION 'Reviewed source evidence is immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION mcq.teacher_approval_ready(account uuid,target uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM mcq.question_versions WHERE id=target AND owner_id=account)
       OR EXISTS(SELECT 1 FROM mcq.teacher_review_events WHERE version_id=target AND action='reject') THEN RETURN false; END IF;
    PERFORM mcq.assert_validation_ready(target,account);
    RETURN true;
EXCEPTION WHEN check_violation THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION mcq.teacher_approval_ready(uuid,uuid) FROM PUBLIC;

-- The trusted API supplies the authenticated account, never a client owner ID.
-- Runtime callers cannot write events/releases directly. No dynamic SQL.
CREATE FUNCTION mcq.teacher_review_action(account uuid,target uuid,retry_key uuid,operation text,body jsonb) RETURNS jsonb
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
        IF EXISTS(SELECT 1 FROM mcq.teacher_review_events WHERE version_id=target AND action='reject') THEN
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

CREATE FUNCTION mcq.assert_teacher_release_current(target uuid) RETURNS void
LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE approval teacher_review_events; release question_releases; latest uuid;
BEGIN
    SELECT * INTO release FROM question_releases WHERE version_id=target;
    IF EXISTS(SELECT 1 FROM teacher_review_events WHERE version_id=target AND action='reject') THEN
        RAISE EXCEPTION 'Rejected versions require editing' USING ERRCODE='23514';
    END IF;
    IF release.teacher_review_id IS NOT NULL THEN
        SELECT * INTO approval FROM teacher_review_events WHERE id=release.teacher_review_id;
        SELECT id INTO latest FROM validation_reports WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 1;
        IF approval.validation_report_id IS DISTINCT FROM latest THEN
            RAISE EXCEPTION 'Teacher approval must reference current validation' USING ERRCODE='23514';
        END IF;
    END IF;
END $$;
REVOKE ALL ON FUNCTION mcq.assert_teacher_release_current(uuid) FROM PUBLIC;

CREATE OR REPLACE FUNCTION mcq.validation_release_gate() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE evidence uuid; latest uuid;
BEGIN
    IF NEW.state='approved' THEN
        PERFORM assert_validation_ready(NEW.version_id,NEW.reviewed_by);
        IF EXISTS(SELECT 1 FROM teacher_review_events WHERE version_id=NEW.version_id AND action='reject') THEN
            RAISE EXCEPTION 'Rejected versions require editing' USING ERRCODE='23514';
        END IF;
        IF NEW.teacher_review_id IS NOT NULL THEN
            SELECT validation_report_id INTO evidence FROM teacher_review_events WHERE id=NEW.teacher_review_id;
            SELECT id INTO latest FROM validation_reports WHERE version_id=NEW.version_id ORDER BY created_at DESC,id DESC LIMIT 1;
            IF evidence IS DISTINCT FROM latest THEN RAISE EXCEPTION 'Approval evidence is stale' USING ERRCODE='23514'; END IF;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION mcq.validation_publish_gate() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE item record;
BEGIN
    IF OLD.state='draft' AND NEW.state='published' THEN
        FOR item IN SELECT r.version_id,r.reviewed_by FROM question_releases r
                    JOIN assessment_questions a ON a.version_id=r.version_id WHERE a.assessment_id=NEW.id LOOP
            PERFORM assert_validation_ready(item.version_id,item.reviewed_by);
            PERFORM assert_teacher_release_current(item.version_id);
        END LOOP;
    END IF;
    RETURN NEW;
END $$;

-- These callees now run within the restricted SECURITY DEFINER boundary.
-- Put pg_temp last so temporary shadow tables cannot replace trusted relations.
ALTER FUNCTION mcq.check_options() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.check_release() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.seal_sources() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.assert_validation_ready(uuid,uuid) SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.validation_corpus(uuid,uuid) SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.validation_release_gate() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.validation_publish_gate() SET search_path=pg_catalog,mcq,pg_temp;
ALTER FUNCTION mcq.assert_teacher_release_current(uuid) SET search_path=pg_catalog,mcq,pg_temp;
