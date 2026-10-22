-- Deterministic validation is separate from AI judgments and teacher approval.
CREATE FUNCTION mcq.validation_corpus(account uuid, excluded_question uuid) RETURNS text
LANGUAGE sql STABLE SET search_path=mcq,public AS $$
    SELECT md5(COALESCE(string_agg(id::text,',' ORDER BY id),'')) FROM (
        SELECT DISTINCT ON (v.question_id) v.id FROM question_versions v
        JOIN questions q ON q.id=v.question_id AND q.owner_id=v.owner_id
        WHERE v.owner_id=account AND v.question_id<>excluded_question AND NOT q.archived
        ORDER BY v.question_id,v.version DESC
    ) corpus
$$;
REVOKE ALL ON FUNCTION mcq.validation_corpus(uuid,uuid) FROM PUBLIC;

CREATE TABLE mcq.validation_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    version_id uuid NOT NULL,
    idempotency_key uuid NOT NULL,
    policy_version text NOT NULL CHECK (policy_version='deterministic-validation-v1'),
    verifier_report_id uuid,
    corpus_hash text NOT NULL CHECK (corpus_hash ~ '^[a-f0-9]{32}$'),
    schema_pass boolean NOT NULL,
    source_pass boolean NOT NULL,
    duplicate_status text NOT NULL CHECK (duplicate_status IN ('pass','fail','incomplete')),
    math_status text NOT NULL CHECK (math_status IN ('pass','fail','unsupported','not_applicable')),
    technical_pass boolean NOT NULL,
    publication_eligible boolean NOT NULL DEFAULT false CHECK (NOT publication_eligible),
    result jsonb NOT NULL CHECK (jsonb_typeof(result)='object'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY(version_id,owner_id) REFERENCES mcq.question_versions(id,owner_id),
    FOREIGN KEY(verifier_report_id,owner_id) REFERENCES mcq.verifier_reports(id,owner_id),
    UNIQUE(owner_id,idempotency_key),
    CHECK (NOT technical_pass OR (schema_pass AND source_pass AND duplicate_status='pass'
        AND math_status IN ('pass','not_applicable') AND verifier_report_id IS NOT NULL))
);
CREATE INDEX validation_history_idx ON mcq.validation_reports(owner_id,version_id,created_at DESC,id DESC);
CREATE TRIGGER preserve_validation_report BEFORE UPDATE OR DELETE ON mcq.validation_reports
    FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
REVOKE ALL ON mcq.validation_reports FROM PUBLIC;

CREATE FUNCTION mcq.guard_validation_report() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE q question_versions; ai verifier_reports;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.owner_id::text,10));
    SELECT * INTO q FROM question_versions WHERE id=NEW.version_id FOR UPDATE;
    IF NEW.verifier_report_id IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM verifier_reports WHERE id=NEW.verifier_report_id AND version_id=NEW.version_id AND owner_id=NEW.owner_id) THEN
        RAISE EXCEPTION 'Verifier evidence belongs to another draft' USING ERRCODE='23514';
    END IF;
    IF NEW.technical_pass THEN
        SELECT * INTO ai FROM verifier_reports WHERE version_id=q.id ORDER BY created_at DESC,id DESC LIMIT 1;
        IF NOT EXISTS(SELECT 1 FROM generation_runs WHERE id=q.generation_run_id AND settings->>'mode'='ollama')
           OR ai.id IS DISTINCT FROM NEW.verifier_report_id OR ai.mode IS DISTINCT FROM 'ollama'
           OR ai.recommendation IS DISTINCT FROM 'PASS'
           OR (ai.result->'ai_executed') IS DISTINCT FROM 'true'::jsonb
           OR (ai.result->'blind_option') IS DISTINCT FROM to_jsonb(q.correct_option)
           OR (q.question_type='numerical' AND NEW.math_status<>'pass')
           OR NEW.corpus_hash<>validation_corpus(NEW.owner_id,q.question_id)
           OR EXISTS(SELECT 1 FROM question_versions WHERE question_id=q.question_id AND version>q.version)
           OR EXISTS(SELECT 1 FROM questions WHERE id=q.question_id AND archived) THEN
            RAISE EXCEPTION 'Technical readiness requires current real evidence and supported validation' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER validation_report_gate BEFORE INSERT ON mcq.validation_reports
    FOR EACH ROW EXECUTE FUNCTION mcq.guard_validation_report();
REVOKE ALL ON FUNCTION mcq.guard_validation_report() FROM PUBLIC;

CREATE FUNCTION mcq.assert_validation_ready(target uuid, reviewer uuid) RETURNS void
LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE q question_versions; v validation_reports; ai verifier_reports;
BEGIN
    SELECT * INTO q FROM question_versions WHERE id=target;
    PERFORM pg_advisory_xact_lock(hashtextextended(q.owner_id::text,10));
    PERFORM 1 FROM question_versions WHERE id=target FOR UPDATE;
    SELECT * INTO v FROM validation_reports WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 1;
    SELECT * INTO ai FROM verifier_reports WHERE version_id=target ORDER BY created_at DESC,id DESC LIMIT 1;
    IF q.id IS NULL
       OR (reviewer IS NOT NULL AND (reviewer IS DISTINCT FROM q.owner_id
           OR NOT EXISTS(SELECT 1 FROM user_roles WHERE user_id=reviewer AND role='teacher')))
       OR (reviewer IS NULL AND NOT EXISTS(SELECT 1 FROM user_roles WHERE user_id=q.owner_id AND role='student'))
       OR NOT EXISTS(SELECT 1 FROM users WHERE id=q.owner_id AND active)
       OR EXISTS(SELECT 1 FROM question_versions WHERE question_id=q.question_id AND version>q.version)
       OR EXISTS(SELECT 1 FROM questions WHERE id=q.question_id AND archived)
       OR EXISTS(SELECT 1 FROM question_sources s JOIN chunks c ON c.id=s.chunk_id JOIN documents d ON d.id=c.document_id JOIN materials m ON m.id=d.material_id WHERE s.version_id=target AND m.archived)
       OR v.id IS NULL OR NOT v.technical_pass OR v.policy_version<>'deterministic-validation-v1'
       OR v.verifier_report_id IS DISTINCT FROM ai.id OR ai.recommendation IS DISTINCT FROM 'PASS'
       OR v.corpus_hash<>validation_corpus(q.owner_id,q.question_id) THEN
        RAISE EXCEPTION 'Release requires fresh validation, current AI evidence and eligible owner/reviewer' USING ERRCODE='23514';
    END IF;
END $$;
REVOKE ALL ON FUNCTION mcq.assert_validation_ready(uuid,uuid) FROM PUBLIC;

CREATE FUNCTION mcq.validation_release_gate() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
BEGIN
    IF NEW.state='approved' THEN PERFORM assert_validation_ready(NEW.version_id,NEW.reviewed_by); END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER validation_release_gate BEFORE INSERT OR UPDATE ON mcq.question_releases
    FOR EACH ROW EXECUTE FUNCTION mcq.validation_release_gate();
REVOKE ALL ON FUNCTION mcq.validation_release_gate() FROM PUBLIC;

CREATE FUNCTION mcq.validation_publish_gate() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
DECLARE item record;
BEGIN
    IF OLD.state='draft' AND NEW.state='published' THEN
        FOR item IN SELECT r.version_id,r.reviewed_by FROM question_releases r
                    JOIN assessment_questions a ON a.version_id=r.version_id WHERE a.assessment_id=NEW.id LOOP
            PERFORM assert_validation_ready(item.version_id,item.reviewed_by);
        END LOOP;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER validation_publish_gate BEFORE UPDATE ON mcq.assessments
    FOR EACH ROW EXECUTE FUNCTION mcq.validation_publish_gate();
REVOKE ALL ON FUNCTION mcq.validation_publish_gate() FROM PUBLIC;
