-- Read-only operational analytics. Snapshot rows, not mutable assessment items.
CREATE FUNCTION mcq.analytics_data(account uuid,audience text,target uuid,start_at integer,page_size integer,ranking boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mcq,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 IF audience NOT IN ('student','teacher') OR NOT EXISTS(
  SELECT 1 FROM mcq.users u JOIN mcq.user_roles r ON r.user_id=u.id
  WHERE u.id=account AND u.active AND r.role=audience
 ) THEN RETURN jsonb_build_object('error','ANALYTICS_FORBIDDEN'); END IF;
 IF start_at IS NULL OR start_at<0 OR page_size IS NULL OR page_size NOT BETWEEN 1 AND 50
 OR (audience='student' AND (target IS NOT NULL OR ranking))
 OR (ranking AND target IS NULL) THEN RETURN jsonb_build_object('error','ANALYTICS_INVALID'); END IF;
 IF target IS NOT NULL AND NOT EXISTS(SELECT 1 FROM mcq.assessments WHERE id=target AND owner_id=account AND kind='classroom')
 THEN RETURN jsonb_build_object('error','ANALYTICS_NOT_FOUND'); END IF;
 WITH scoped AS MATERIALIZED (
  SELECT a.*,e.title,e.kind,e.release_policy,e.state AS assessment_state,s.deadline,
    (a.state<>'in_progress' AND (audience='teacher' OR e.release_policy='after_submit' OR e.state='closed')) AS visible
  FROM mcq.attempts a JOIN mcq.assessments e ON e.id=a.assessment_id
  JOIN mcq.attempt_sessions s ON s.attempt_id=a.id
  WHERE CASE WHEN audience='student' THEN a.student_id=account ELSE e.owner_id=account AND e.kind='classroom' END
    AND (target IS NULL OR e.id=target)
 ), item_data AS MATERIALIZED (
  SELECT a.id AS attempt_id,a.student_id,i.version_id,i.points,v.stem,v.topic_id,t.name AS topic,
    v.difficulty,v.question_type,ans.selected_option,ans.is_correct,ans.awarded_points,
    COALESCE(r.state='approved',false) AS eligible
  FROM scoped a JOIN mcq.attempt_items i ON i.attempt_id=a.id
  JOIN mcq.question_versions v ON v.id=i.version_id JOIN mcq.topics t ON t.id=v.topic_id
  LEFT JOIN mcq.answers ans ON ans.attempt_id=i.attempt_id AND ans.version_id=i.version_id
  LEFT JOIN mcq.question_releases r ON r.version_id=i.version_id WHERE a.visible
 ), scores AS MATERIALIZED (
  SELECT a.id,a.student_id,a.state,a.submitted_at,sum(i.points) AS possible_points,
    sum(COALESCE(i.awarded_points,0)) AS awarded_points,
    100*sum(COALESCE(i.awarded_points,0))/NULLIF(sum(i.points),0) AS percent,
    count(*) FILTER(WHERE NOT i.eligible) AS excluded_items,
    greatest(0,extract(epoch FROM (least(a.submitted_at,COALESCE(a.deadline,a.submitted_at))-a.started_at))) AS elapsed_seconds
  FROM scoped a JOIN item_data i ON i.attempt_id=a.id
  GROUP BY a.id,a.student_id,a.state,a.submitted_at,a.deadline,a.started_at
 ), grouped AS (
  SELECT g.dimension,g.key,g.label,count(*) AS items,
    count(*) FILTER(WHERE i.selected_option IS NOT NULL) AS answered,
    count(*) FILTER(WHERE i.is_correct) AS correct,
    count(*) FILTER(WHERE i.selected_option IS NOT NULL AND NOT i.is_correct) AS incorrect,
    count(*) FILTER(WHERE i.selected_option IS NULL) AS skipped,
    round(100.0*count(*) FILTER(WHERE i.is_correct)/NULLIF(count(*) FILTER(WHERE i.selected_option IS NOT NULL),0),1) AS accuracy
  FROM item_data i CROSS JOIN LATERAL (VALUES
    ('topic',i.topic_id::text,i.topic),('difficulty',i.difficulty,i.difficulty),('type',i.question_type,i.question_type)
  ) g(dimension,key,label) WHERE i.eligible GROUP BY g.dimension,g.key,g.label
 ), missed AS (
  SELECT version_id,stem,count(*) AS exposures,count(DISTINCT student_id) AS students,
    count(*) FILTER(WHERE is_correct) AS correct,
    count(*) FILTER(WHERE selected_option IS NOT NULL AND NOT is_correct) AS incorrect,
    count(*) FILTER(WHERE selected_option IS NULL) AS skipped,
    round(100.0*count(*) FILTER(WHERE NOT is_correct)/NULLIF(count(*),0),1) AS missed_percent
  FROM item_data WHERE eligible GROUP BY version_id,stem
 ), reports AS MATERIALIZED (
  SELECT f.* FROM mcq.feedback f JOIN scoped a ON a.id=f.attempt_id
 ), best AS (
  SELECT DISTINCT ON(student_id) student_id,percent,id FROM scores
  WHERE ranking AND state='submitted' AND excluded_items=0
  ORDER BY student_id,percent DESC,submitted_at,id
 ), ranked AS (
  SELECT rank() OVER(ORDER BY b.percent DESC) AS rank,u.display_name,round(b.percent,1) AS score_percent,b.id AS attempt_id
  FROM best b JOIN mcq.users u ON u.id=b.student_id
 )
 SELECT jsonb_build_object(
  'scope',audience,'assessment_id',target,'generated_at',statement_timestamp(),
  'assessment_title',(SELECT title FROM mcq.assessments WHERE id=target),
  'summary',(SELECT jsonb_build_object('attempts',count(*),'students',count(DISTINCT student_id),
    'submitted',count(*) FILTER(WHERE state='submitted'),'expired',count(*) FILTER(WHERE state='expired'),
    'in_progress',count(*) FILTER(WHERE state='in_progress'),
    'overdue',count(*) FILTER(WHERE state='in_progress' AND deadline<=statement_timestamp()),
    'withheld',count(*) FILTER(WHERE state<>'in_progress' AND NOT visible),
    'scored_attempts',(SELECT count(*) FROM scores),
    'average_score',(SELECT round(avg(percent),1) FROM scores),
    'average_elapsed_seconds',(SELECT round(avg(elapsed_seconds),1) FROM scores),
    'items',(SELECT count(*) FROM item_data),
    'excluded_items',(SELECT count(*) FROM item_data WHERE NOT eligible),
    'answered',(SELECT count(*) FROM item_data WHERE eligible AND selected_option IS NOT NULL),
    'correct',(SELECT count(*) FROM item_data WHERE eligible AND is_correct),
    'incorrect',(SELECT count(*) FROM item_data WHERE eligible AND selected_option IS NOT NULL AND NOT is_correct),
    'skipped',(SELECT count(*) FROM item_data WHERE eligible AND selected_option IS NULL),
    'accuracy',(SELECT round(100.0*count(*) FILTER(WHERE is_correct)/NULLIF(count(*) FILTER(WHERE selected_option IS NOT NULL),0),1) FROM item_data WHERE eligible)
  ) FROM scoped),
  'breakdowns',COALESCE((SELECT jsonb_agg(g ORDER BY dimension,label,key) FROM grouped g),'[]'::jsonb),
  'missed_items',CASE WHEN audience='teacher' THEN COALESCE((SELECT jsonb_agg(m) FROM
    (SELECT * FROM missed ORDER BY missed_percent DESC,exposures DESC,version_id LIMIT 20) m),'[]'::jsonb) ELSE '[]'::jsonb END,
  'feedback',(SELECT jsonb_build_object('reports',count(*),
    'issue_reporters',count(DISTINCT student_id) FILTER(WHERE category<>'rating'),
    'open_issues',count(*) FILTER(WHERE category<>'rating' AND state IN ('open','reviewing')),
    'helpful',count(*) FILTER(WHERE rating='helpful'),'poor',count(*) FILTER(WHERE rating='poor')) FROM reports),
  'history',COALESCE((SELECT jsonb_agg(h ORDER BY h.started_at DESC,h.id DESC) FROM (
    SELECT a.id,a.assessment_id,a.title,a.kind,a.state,a.started_at,a.submitted_at,a.attempt_number,a.visible AS results_visible,
      CASE WHEN audience='teacher' THEN u.display_name ELSE NULL END AS student_name,
      round(s.percent,1) AS score_percent,s.awarded_points,s.possible_points,s.excluded_items,round(s.elapsed_seconds,1) AS elapsed_seconds
    FROM scoped a JOIN mcq.users u ON u.id=a.student_id LEFT JOIN scores s ON s.id=a.id
    ORDER BY a.started_at DESC,a.id DESC OFFSET start_at LIMIT page_size
  ) h),'[]'::jsonb),
  'offset',start_at,'limit',page_size,
  'ranking_enabled',ranking,'ranking',COALESCE((SELECT jsonb_agg(r ORDER BY rank,display_name,attempt_id) FROM ranked r),'[]'::jsonb)
 ) INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION mcq.analytics_data(uuid,text,uuid,integer,integer,boolean) FROM PUBLIC;
