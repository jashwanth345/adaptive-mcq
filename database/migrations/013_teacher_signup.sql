-- Local classroom signup: new teacher accounts own only their own workspace.
-- Existing accounts cannot be promoted through registration.
CREATE FUNCTION mcq.register_teacher(p_email text, p_name text, p_password_hash text)
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
    INSERT INTO mcq.user_roles(user_id,role) VALUES(new_user,'teacher');
    INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id)
        VALUES(new_user,'auth.register_teacher','user',new_user);
    RETURN new_user;
END $$;
REVOKE ALL ON FUNCTION mcq.register_teacher(text,text,text) FROM PUBLIC;
