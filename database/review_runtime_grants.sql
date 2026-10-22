-- Trusted operator after migration 006 and prior phase grants.
-- Functions validate owned teacher identity and release gates; no direct writes.
GRANT SELECT ON mcq.teacher_review_events TO :"runtime_role";
GRANT EXECUTE ON FUNCTION mcq.teacher_approval_ready(uuid,uuid),
    mcq.teacher_review_action(uuid,uuid,uuid,text,jsonb) TO :"runtime_role";
