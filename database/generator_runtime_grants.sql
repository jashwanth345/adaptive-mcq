-- Trusted operator; after all Phase 4–9 runtime grants. No publication writes.
GRANT SELECT ON mcq.jobs,mcq.generation_runs,mcq.question_versions,mcq.options,
  mcq.question_sources,mcq.question_verifications,mcq.question_releases TO :"runtime_role";
GRANT INSERT (owner_id,kind,state,idempotency_key,parameters,stage,attempts) ON mcq.jobs TO :"runtime_role";
GRANT INSERT (owner_id,job_id,generator_model,model_digest,prompt_version,settings) ON mcq.generation_runs TO :"runtime_role";
GRANT INSERT (owner_id) ON mcq.questions TO :"runtime_role";
GRANT INSERT (question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type) ON mcq.question_versions TO :"runtime_role";
GRANT INSERT (version_id,ordinal,content) ON mcq.options TO :"runtime_role";
GRANT INSERT (version_id,chunk_id,owner_id,evidence_quote) ON mcq.question_sources TO :"runtime_role";
-- Source trigger takes FOR UPDATE; immutable-version trigger rejects any UPDATE.
GRANT UPDATE (id) ON mcq.question_versions TO :"runtime_role";
