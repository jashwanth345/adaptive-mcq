-- Apply as migration operator after 012. No direct table writes or global exports.
GRANT EXECUTE ON FUNCTION mcq.evaluation_access(uuid,text,uuid,uuid,jsonb),mcq.evaluation_events(uuid,uuid[]) TO :"runtime_role";
