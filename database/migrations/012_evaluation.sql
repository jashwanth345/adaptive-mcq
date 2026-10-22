-- Evaluation-only artifacts cannot reference releases or become classroom questions.
CREATE TABLE mcq.evaluation_runs (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES mcq.users,idempotency_key uuid NOT NULL,
 result jsonb NOT NULL CHECK(result->>'format'='evaluation-run-v1' AND result->>'mode'='mock'),
 summary jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(owner_id,idempotency_key)
);
CREATE TRIGGER preserve_evaluation_run BEFORE UPDATE OR DELETE ON mcq.evaluation_runs FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation();
REVOKE ALL ON mcq.evaluation_runs FROM PUBLIC;

CREATE FUNCTION mcq.evaluation_access(account uuid,op text,target uuid,retry uuid,body jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE row mcq.evaluation_runs;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='teacher')
 THEN RETURN jsonb_build_object('error','EVALUATION_FORBIDDEN'); END IF;
 IF op='list' THEN
  RETURN jsonb_build_object('items',COALESCE((SELECT jsonb_agg(x ORDER BY x.created_at DESC,x.id) FROM
   (SELECT id,created_at,result->>'evidence_status' AS evidence_status FROM mcq.evaluation_runs WHERE owner_id=account) x),'[]'::jsonb));
 ELSIF op='get' THEN
  SELECT * INTO row FROM mcq.evaluation_runs WHERE id=target AND owner_id=account;
 ELSIF op IN ('retry','save') THEN
  IF retry IS NULL THEN RETURN jsonb_build_object('error','EVALUATION_INVALID'); END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(account::text,19));
  SELECT * INTO row FROM mcq.evaluation_runs WHERE owner_id=account AND idempotency_key=retry;
  IF row.id IS NULL AND op='save' THEN
   IF (SELECT count(*) FROM mcq.evaluation_runs WHERE owner_id=account)>=20 THEN RETURN jsonb_build_object('error','EVALUATION_LIMIT'); END IF;
   IF body->'run'->>'format' IS DISTINCT FROM 'evaluation-run-v1' OR body->'run'->>'mode' IS DISTINCT FROM 'mock'
    OR body->'run'->>'completed' IS DISTINCT FROM 'true' OR octet_length(body::text)>2000000
    OR body->'summary'->>'format' IS DISTINCT FROM 'evaluation-summary-v1'
   THEN RETURN jsonb_build_object('error','EVALUATION_INVALID'); END IF;
   INSERT INTO mcq.evaluation_runs(id,owner_id,idempotency_key,result,summary)
   VALUES((body->'run'->>'id')::uuid,account,retry,body->'run',body->'summary') RETURNING * INTO row;
   INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(account,'evaluation.smoke_saved','evaluation_run',row.id);
  END IF;
 ELSE RETURN jsonb_build_object('error','EVALUATION_INVALID'); END IF;
 IF row.id IS NULL THEN
  RETURN CASE WHEN op='retry' THEN jsonb_build_object('found',false) ELSE jsonb_build_object('error','EVALUATION_NOT_FOUND') END;
 END IF;
 RETURN jsonb_build_object('found',true,'id',row.id,'created_at',row.created_at,'run',row.result,'summary',row.summary);
END $$;
REVOKE ALL ON FUNCTION mcq.evaluation_access(uuid,text,uuid,uuid,jsonb) FROM PUBLIC;

CREATE FUNCTION mcq.evaluation_events(account uuid,targets uuid[]) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='teacher')
 THEN RETURN jsonb_build_object('error','EVALUATION_FORBIDDEN'); END IF;
 IF targets IS NULL OR cardinality(targets) NOT BETWEEN 1 AND 8 OR array_position(targets,NULL) IS NOT NULL
 THEN RETURN jsonb_build_object('error','EVALUATION_INVALID'); END IF;
 IF EXISTS(SELECT 1 FROM unnest(targets) AS requested(id) WHERE NOT EXISTS(SELECT 1 FROM mcq.assessments a WHERE a.id=requested.id AND a.owner_id=account AND a.kind='classroom'))
 THEN RETURN jsonb_build_object('error','EVALUATION_NOT_FOUND'); END IF;
 SELECT COALESCE(jsonb_agg(x ORDER BY x.submitted_at,x.attempt_id,x.version_id),'[]'::jsonb) INTO result FROM (
  SELECT a.student_id,a.id AS attempt_id,a.assessment_id,a.submitted_at,e.version_id,e.topic_id,v.difficulty,ans.is_correct
  FROM mcq.mastery_evidence e JOIN mcq.attempts a ON a.id=e.attempt_id
  JOIN mcq.assessments exam ON exam.id=a.assessment_id AND exam.owner_id=account
  JOIN mcq.answers ans ON ans.attempt_id=a.id AND ans.version_id=e.version_id
  JOIN mcq.question_versions v ON v.id=e.version_id
  JOIN mcq.question_releases rel ON rel.version_id=e.version_id AND rel.state='approved'
  WHERE a.assessment_id=ANY(targets) AND a.state='submitted' AND ans.selected_option IS NOT NULL
    AND e.algorithm_version='bounded-performance-v1' AND (exam.release_policy='after_submit' OR exam.state='closed')
  ORDER BY a.submitted_at,a.id,e.version_id LIMIT 10001
 ) x;
 IF jsonb_array_length(result)>10000 THEN RETURN jsonb_build_object('error','EVALUATION_EXPORT_LIMIT'); END IF;
 RETURN jsonb_build_object('events',result);
END $$;
REVOKE ALL ON FUNCTION mcq.evaluation_events(uuid,uuid[]) FROM PUBLIC;
