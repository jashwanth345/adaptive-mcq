-- Trusted operator, after migration 004 and the Phase 4–10 grants.
GRANT SELECT ON mcq.verifier_reports TO :"runtime_role";
GRANT INSERT(owner_id,version_id,job_id,mode,recommendation,result) ON mcq.verifier_reports TO :"runtime_role";
-- No UPDATE/DELETE, release writes or question_verifications writes.
