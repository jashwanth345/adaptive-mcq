-- Operator-applied AFTER migration 003, in the intended database.
-- psql -v runtime_role=adaptive_mcq_app -f database/auth_runtime_grants.sql
-- The role must already exist, must be non-administrative, and must not own schemas.
-- Never run this against the migration-owner role.
\set ON_ERROR_STOP on
BEGIN;
GRANT USAGE ON SCHEMA mcq, mcq_meta TO :"runtime_role";
GRANT SELECT ON mcq_meta.schema_migrations TO :"runtime_role";
GRANT SELECT ON mcq.users, mcq.user_roles TO :"runtime_role";
GRANT UPDATE(password_hash) ON mcq.users TO :"runtime_role";
GRANT EXECUTE ON FUNCTION mcq.register_student(text,text,text) TO :"runtime_role";
GRANT EXECUTE ON FUNCTION mcq.register_teacher(text,text,text) TO :"runtime_role";
GRANT SELECT, INSERT ON mcq.auth_sessions TO :"runtime_role";
GRANT UPDATE(revoked_at) ON mcq.auth_sessions TO :"runtime_role";
GRANT SELECT, INSERT, UPDATE ON mcq.auth_rate_limits TO :"runtime_role";
GRANT INSERT ON mcq.audit_events TO :"runtime_role";
GRANT USAGE ON SEQUENCE mcq.audit_events_id_seq TO :"runtime_role";
COMMIT;
