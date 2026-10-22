-- Run as the trusted database owner, after authentication grants.
-- psql -v runtime_role=adaptive_mcq_app -f database/student_runtime_grants.sql
GRANT SELECT (user_id, preferred_difficulty) ON mcq.student_profiles TO :"runtime_role";
GRANT UPDATE (preferred_difficulty) ON mcq.student_profiles TO :"runtime_role";
GRANT SELECT (course_id, student_id, active, joined_at) ON mcq.course_memberships TO :"runtime_role";
GRANT SELECT (id, title) ON mcq.courses TO :"runtime_role";
GRANT SELECT (owner_id, archived) ON mcq.materials TO :"runtime_role";
GRANT SELECT (id, assessment_id, student_id, attempt_number, state, started_at, submitted_at) ON mcq.attempts TO :"runtime_role";
GRANT SELECT (id, title, kind) ON mcq.assessments TO :"runtime_role";
GRANT SELECT (student_id) ON mcq.feedback TO :"runtime_role";
-- No access to answers, keys, mastery writes or attempt/enrollment creation.
