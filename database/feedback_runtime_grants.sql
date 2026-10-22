-- Trusted operator after migration 010. Never grant direct feedback/release writes.
GRANT EXECUTE ON FUNCTION mcq.feedback_action(uuid,uuid,uuid,text,jsonb),
 mcq.feedback_history(uuid,integer,integer),mcq.feedback_queue(uuid,integer,integer),
 mcq.feedback_detail(uuid,uuid,integer,integer) TO :"runtime_role";

GRANT EXECUTE ON FUNCTION mcq.feedback_confirmed(uuid,uuid) TO :"runtime_role";
