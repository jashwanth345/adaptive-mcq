-- Apply as trusted operator after migration 007 and previous module grants.
GRANT SELECT ON mcq.assessment_questions,mcq.reference_codes,mcq.assessment_participants,
    mcq.assessment_admissions,mcq.assessment_operations TO :"runtime_role";
GRANT EXECUTE ON FUNCTION mcq.assessment_action(uuid,uuid,uuid,text,jsonb,text),
    mcq.assessment_ready(uuid),mcq.assessment_access(uuid,uuid,uuid),mcq.join_assessment(uuid,text) TO :"runtime_role";
