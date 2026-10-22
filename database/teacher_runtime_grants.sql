-- Run as the database owner after authentication grants. No role is created here.
-- psql -v runtime_role=adaptive_mcq_app -f database/teacher_runtime_grants.sql
GRANT SELECT ON mcq.courses, mcq.topics, mcq.materials, mcq.questions, mcq.assessments TO :"runtime_role";
GRANT INSERT (owner_id, title) ON mcq.courses TO :"runtime_role";
GRANT INSERT (owner_id, course_id, name) ON mcq.topics TO :"runtime_role";
-- No UPDATE/DELETE or assessment/question publication permission is granted.
