CREATE FUNCTION mcq.learning_data(account uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE preferred text; evidence jsonb; candidates jsonb; total integer;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id WHERE u.id=account AND u.active AND r.role='student') THEN RETURN jsonb_build_object('error','ATTEMPT_FORBIDDEN'); END IF;
 SELECT preferred_difficulty INTO preferred FROM mcq.student_profiles WHERE user_id=account;
 SELECT count(*) INTO total FROM mcq.mastery_evidence WHERE student_id=account AND algorithm_version='bounded-performance-v1';
 SELECT COALESCE(jsonb_agg(x ORDER BY x.submitted_at,x.attempt_id,x.version_id),'[]'::jsonb) INTO evidence FROM (
   SELECT e.topic_id,t.name AS topic,v.difficulty,e.version_id,e.attempt_id,ans.is_correct,a.submitted_at
   FROM mcq.mastery_evidence e JOIN mcq.question_versions v ON v.id=e.version_id JOIN mcq.topics t ON t.id=e.topic_id
   JOIN mcq.attempts a ON a.id=e.attempt_id JOIN mcq.assessments exam ON exam.id=a.assessment_id
   JOIN mcq.answers ans ON ans.attempt_id=e.attempt_id AND ans.version_id=e.version_id
   JOIN mcq.question_releases r ON r.version_id=e.version_id AND r.state='approved'
   WHERE e.student_id=account AND e.algorithm_version='bounded-performance-v1' AND a.state='submitted'
     AND ans.selected_option IS NOT NULL AND (exam.release_policy='after_submit' OR exam.state='closed')
   ORDER BY a.submitted_at DESC,e.attempt_id DESC,e.version_id DESC LIMIT 5000
 ) x;
 -- Candidate selection never borrows a teacher's private bank or reveals solutions.
 SELECT COALESCE(jsonb_agg(x),'[]'::jsonb) INTO candidates FROM (
   SELECT v.id AS version_id,v.topic_id,t.name AS topic,v.difficulty,v.question_type,v.cognitive_level
   FROM mcq.question_versions v JOIN mcq.topics t ON t.id=v.topic_id
   WHERE v.owner_id=account AND NOT EXISTS(SELECT 1 FROM mcq.attempt_items i JOIN mcq.attempts a ON a.id=i.attempt_id WHERE a.student_id=account AND i.version_id=v.id)
     AND mcq.practice_ready(account,v.id)
   ORDER BY v.created_at,v.id LIMIT 50
 ) x;
 RETURN jsonb_build_object('preferred_difficulty',COALESCE(preferred,'easy'),'evidence',evidence,'candidates',candidates,'retained_evidence_count',total);
END $$;
REVOKE ALL ON FUNCTION mcq.learning_data(uuid) FROM PUBLIC;
