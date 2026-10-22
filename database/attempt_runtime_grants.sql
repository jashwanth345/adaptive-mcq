-- Trusted operator, after migration 008 and existing module grants.
GRANT EXECUTE ON FUNCTION mcq.attempt_action(uuid,uuid,uuid,text,jsonb),mcq.attempt_view(uuid,uuid),mcq.practice_ready(uuid,uuid) TO :"runtime_role";
-- Answers, permutations, keys and writes stay behind scoped functions.
