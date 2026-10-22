SET LOCAL search_path = mcq, public;

CREATE TABLE auth_sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at)
);
CREATE INDEX auth_sessions_user_idx ON auth_sessions(user_id);
CREATE INDEX auth_sessions_expiry_idx ON auth_sessions(expires_at);

CREATE TABLE auth_rate_limits (
    bucket_key text PRIMARY KEY CHECK (bucket_key ~ '^[0-9a-f]{64}$'),
    attempts integer NOT NULL CHECK (attempts > 0),
    expires_at timestamptz NOT NULL
);
CREATE INDEX auth_rate_limits_expiry_idx ON auth_rate_limits(expires_at);

CREATE FUNCTION guard_auth_session() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - 'revoked_at') IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at')
       OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN
        RAISE EXCEPTION 'Session identity and revocation are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER auth_session_guard BEFORE UPDATE ON auth_sessions
    FOR EACH ROW EXECUTE FUNCTION guard_auth_session();

-- The app can enroll a student but cannot supply a role or insert user_roles directly.
-- Only the trusted migration owner owns this function. No dynamic SQL is used.
CREATE FUNCTION register_student(p_email text, p_name text, p_password_hash text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, mcq
AS $$
DECLARE new_user uuid;
BEGIN
    IF p_password_hash NOT LIKE '$argon2id$%' THEN
        RAISE EXCEPTION 'An Argon2id hash is required' USING ERRCODE = '23514';
    END IF;
    INSERT INTO mcq.users(email,display_name,password_hash)
        VALUES(p_email,p_name,p_password_hash) ON CONFLICT(email) DO NOTHING
        RETURNING id INTO new_user;
    IF new_user IS NULL THEN RETURN NULL; END IF;
    INSERT INTO mcq.user_roles(user_id,role) VALUES(new_user,'student');
    INSERT INTO mcq.student_profiles(user_id) VALUES(new_user);
    INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id)
        VALUES(new_user,'auth.register','user',new_user);
    RETURN new_user;
END $$;
REVOKE ALL ON FUNCTION register_student(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION guard_auth_session() FROM PUBLIC;
REVOKE ALL ON auth_sessions,auth_rate_limits FROM PUBLIC;
