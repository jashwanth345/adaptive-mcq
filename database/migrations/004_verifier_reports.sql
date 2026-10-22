-- Advisory component reports are deliberately separate from release-gate evidence.
CREATE TABLE mcq.verifier_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    version_id uuid NOT NULL,
    job_id uuid NOT NULL UNIQUE,
    mode text NOT NULL CHECK (mode IN ('mock','ollama')),
    recommendation text NOT NULL CHECK (recommendation IN ('NOT_EVALUATED','PASS','REGENERATE','REJECT')),
    publication_eligible boolean NOT NULL DEFAULT false CHECK (NOT publication_eligible),
    result jsonb NOT NULL CHECK (jsonb_typeof(result)='object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (version_id,owner_id) REFERENCES mcq.question_versions(id,owner_id),
    FOREIGN KEY (job_id,owner_id) REFERENCES mcq.jobs(id,owner_id),
    CHECK (mode <> 'mock' OR (recommendation='NOT_EVALUATED' AND (result->'ai_executed') IS NOT DISTINCT FROM 'false'::jsonb)),
    CHECK (recommendation <> 'PASS' OR (result->'ai_executed') IS NOT DISTINCT FROM 'true'::jsonb),
    UNIQUE(id,owner_id)
);
CREATE INDEX verifier_reports_history_idx ON mcq.verifier_reports(owner_id,version_id,created_at DESC,id DESC);
CREATE TRIGGER preserve_verifier_report BEFORE UPDATE OR DELETE ON mcq.verifier_reports
    FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
REVOKE ALL ON mcq.verifier_reports FROM PUBLIC;
CREATE FUNCTION mcq.guard_verifier_report() RETURNS trigger LANGUAGE plpgsql SET search_path=mcq,public AS $$
BEGIN
    PERFORM 1 FROM question_versions WHERE id=NEW.version_id FOR UPDATE;
    IF NOT EXISTS(SELECT 1 FROM jobs WHERE id=NEW.job_id AND owner_id=NEW.owner_id AND kind='verify' AND state='completed') THEN
        RAISE EXCEPTION 'Review needs a completed verification job' USING ERRCODE='23514';
    END IF;
    IF NEW.mode='ollama' AND NOT EXISTS(
        SELECT 1 FROM question_versions v JOIN generation_runs g ON g.id=v.generation_run_id
        WHERE v.id=NEW.version_id AND g.settings->>'mode'='ollama') THEN
        RAISE EXCEPTION 'Test drafts cannot receive real AI reports' USING ERRCODE='23514';
    END IF;
    IF EXISTS(SELECT 1 FROM question_releases WHERE version_id=NEW.version_id) THEN
        RAISE EXCEPTION 'Review requires an unreleased draft' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER verifier_report_gate BEFORE INSERT ON mcq.verifier_reports
    FOR EACH ROW EXECUTE FUNCTION mcq.guard_verifier_report();
REVOKE ALL ON FUNCTION mcq.guard_verifier_report() FROM PUBLIC;
