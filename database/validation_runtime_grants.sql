-- Trusted operator after migration 005 and prior phase grants. No release rights.
GRANT SELECT ON mcq.validation_reports TO :"runtime_role";
GRANT INSERT(owner_id,version_id,idempotency_key,policy_version,verifier_report_id,corpus_hash,
    schema_pass,source_pass,duplicate_status,math_status,technical_pass,result) ON mcq.validation_reports TO :"runtime_role";
GRANT SELECT ON mcq.questions TO :"runtime_role";
GRANT EXECUTE ON FUNCTION mcq.validation_corpus(uuid,uuid) TO :"runtime_role";
