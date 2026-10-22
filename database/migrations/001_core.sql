-- Forward-only. Run through migrate.py, which supplies the transaction.
CREATE SCHEMA mcq;
REVOKE ALL ON SCHEMA mcq FROM PUBLIC;
SET LOCAL search_path = mcq, public;

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL CHECK (email = lower(btrim(email)) AND position('@' IN email) > 1),
    display_name text NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 160),
    password_hash text NOT NULL CHECK (length(password_hash) > 20),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (email)
);
CREATE TABLE user_roles (
    user_id uuid NOT NULL REFERENCES users,
    role text NOT NULL CHECK (role IN ('teacher','student')),
    PRIMARY KEY (user_id, role)
);
CREATE TABLE courses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 200),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, owner_id)
);
CREATE TABLE course_memberships (
    course_id uuid NOT NULL REFERENCES courses,
    student_id uuid NOT NULL REFERENCES users,
    active boolean NOT NULL DEFAULT true,
    joined_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (course_id, student_id)
);
CREATE TABLE topics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    course_id uuid,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    FOREIGN KEY (course_id, owner_id) REFERENCES courses (id, owner_id),
    UNIQUE (id, owner_id),
    UNIQUE NULLS NOT DISTINCT (owner_id, course_id, name)
);
CREATE TABLE materials (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 250),
    archived boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, owner_id)
);
CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    storage_key text NOT NULL UNIQUE CHECK (storage_key ~ '^[a-zA-Z0-9_-]+[.]pdf$'),
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0),
    page_count integer NOT NULL CHECK (page_count > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (material_id, owner_id) REFERENCES materials (id, owner_id),
    UNIQUE (material_id, version),
    UNIQUE (id, owner_id)
);
CREATE TABLE chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    page_start integer NOT NULL CHECK (page_start > 0),
    page_end integer NOT NULL CHECK (page_end >= page_start),
    content text NOT NULL CHECK (length(btrim(content)) > 0),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    token_count integer NOT NULL CHECK (token_count > 0),
    splitter_version text NOT NULL,
    FOREIGN KEY (document_id, owner_id) REFERENCES documents (id, owner_id),
    UNIQUE (document_id, ordinal),
    UNIQUE (id, owner_id)
);
CREATE TABLE jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    kind text NOT NULL CHECK (kind IN ('ingest','generate','verify','evaluate')),
    state text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','cancelling','completed','failed','cancelled')),
    idempotency_key uuid NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(parameters) = 'object'),
    stage text,
    lease_owner text,
    lease_expires_at timestamptz,
    heartbeat_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, kind, idempotency_key),
    UNIQUE (id, owner_id),
    CHECK ((lease_owner IS NULL) = (lease_expires_at IS NULL))
);
CREATE INDEX jobs_queue_idx ON jobs (created_at) WHERE state = 'queued';
CREATE TABLE generation_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    generator_model text NOT NULL,
    model_digest text NOT NULL,
    prompt_version text NOT NULL,
    settings jsonb NOT NULL CHECK (jsonb_typeof(settings) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (job_id, owner_id) REFERENCES jobs (id, owner_id),
    UNIQUE (id, owner_id)
);
CREATE TABLE questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    archived boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, owner_id)
);
CREATE TABLE question_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    topic_id uuid NOT NULL,
    generation_run_id uuid,
    stem text NOT NULL CHECK (length(btrim(stem)) > 0),
    explanation text NOT NULL CHECK (length(btrim(explanation)) > 0),
    correct_option smallint NOT NULL CHECK (correct_option BETWEEN 0 AND 3),
    difficulty text NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
    cognitive_level text NOT NULL CHECK (cognitive_level IN ('remember','understand','apply','analyze','evaluate','create')),
    question_type text NOT NULL CHECK (question_type IN ('conceptual','scenario','numerical','code')),
    language text NOT NULL DEFAULT 'en' CHECK (language = 'en'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (question_id, owner_id) REFERENCES questions (id, owner_id),
    FOREIGN KEY (topic_id, owner_id) REFERENCES topics (id, owner_id),
    FOREIGN KEY (generation_run_id, owner_id) REFERENCES generation_runs (id, owner_id),
    UNIQUE (question_id, version),
    UNIQUE (id, owner_id),
    UNIQUE (id, topic_id)
);
CREATE TABLE options (
    version_id uuid NOT NULL REFERENCES question_versions,
    ordinal smallint NOT NULL CHECK (ordinal BETWEEN 0 AND 3),
    content text NOT NULL CHECK (length(btrim(content)) > 0),
    PRIMARY KEY (version_id, ordinal)
);
CREATE UNIQUE INDEX options_content_idx ON options (version_id, lower(btrim(content)));
CREATE TABLE question_sources (
    version_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    evidence_quote text NOT NULL CHECK (length(btrim(evidence_quote)) > 0),
    PRIMARY KEY (version_id, chunk_id),
    FOREIGN KEY (version_id, owner_id) REFERENCES question_versions (id, owner_id),
    FOREIGN KEY (chunk_id, owner_id) REFERENCES chunks (id, owner_id)
);
CREATE TABLE question_verifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id uuid NOT NULL REFERENCES question_versions,
    verifier_model text NOT NULL,
    model_digest text NOT NULL,
    prompt_version text NOT NULL,
    policy_version text NOT NULL,
    status text NOT NULL CHECK (status IN ('PASS','REGENERATE','REJECT')),
    confidence_score smallint CHECK (confidence_score BETWEEN 0 AND 100),
    correctness_score smallint CHECK (correctness_score BETWEEN 0 AND 100),
    clarity_score smallint CHECK (clarity_score BETWEEN 0 AND 100),
    difficulty_score smallint CHECK (difficulty_score BETWEEN 0 AND 100),
    distractor_score smallint CHECK (distractor_score BETWEEN 0 AND 100),
    grounding_score smallint CHECK (grounding_score BETWEEN 0 AND 100),
    duplicate_score smallint CHECK (duplicate_score BETWEEN 0 AND 100),
    blind_option smallint CHECK (blind_option BETWEEN 0 AND 3),
    schema_pass boolean NOT NULL DEFAULT false,
    source_pass boolean NOT NULL DEFAULT false,
    duplicate_pass boolean NOT NULL DEFAULT false,
    math_result text NOT NULL CHECK (math_result IN ('not_applicable','pass','fail','unsupported')),
    review_required boolean NOT NULL DEFAULT true,
    issues jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(issues) = 'array'),
    suggested_fix text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, version_id),
    CHECK (status <> 'PASS' OR (
        confidence_score IS NOT NULL AND correctness_score IS NOT NULL AND clarity_score IS NOT NULL
        AND difficulty_score IS NOT NULL AND distractor_score IS NOT NULL AND grounding_score IS NOT NULL
        AND duplicate_score IS NOT NULL AND blind_option IS NOT NULL
        AND schema_pass AND source_pass AND duplicate_pass AND NOT review_required
        AND math_result IN ('not_applicable','pass')))
);
CREATE TABLE question_releases (
    version_id uuid PRIMARY KEY REFERENCES question_versions,
    verification_id uuid NOT NULL,
    reviewed_by uuid REFERENCES users,
    state text NOT NULL CHECK (state IN ('approved','quarantined')),
    reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (verification_id, version_id) REFERENCES question_verifications (id, version_id)
);
CREATE TABLE assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES users,
    course_id uuid,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 200),
    kind text NOT NULL CHECK (kind IN ('classroom','practice')),
    mode text NOT NULL CHECK (mode IN ('fixed','adaptive')),
    state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','published','closed')),
    time_limit_seconds integer CHECK (time_limit_seconds > 0),
    max_attempts integer NOT NULL DEFAULT 1 CHECK (max_attempts BETWEEN 1 AND 100),
    randomize_questions boolean NOT NULL DEFAULT false,
    randomize_options boolean NOT NULL DEFAULT false,
    release_policy text NOT NULL DEFAULT 'after_submit' CHECK (release_policy IN ('after_submit','after_close')),
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (course_id, owner_id) REFERENCES courses (id, owner_id),
    UNIQUE (id, owner_id),
    CHECK (kind <> 'classroom' OR (mode = 'fixed' AND course_id IS NOT NULL)),
    CHECK (kind <> 'practice' OR course_id IS NULL),
    CHECK ((state = 'draft' AND published_at IS NULL) OR (state <> 'draft' AND published_at IS NOT NULL))
);
CREATE TABLE assessment_questions (
    assessment_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    position integer NOT NULL CHECK (position > 0),
    version_id uuid NOT NULL,
    points numeric(8,2) NOT NULL DEFAULT 1 CHECK (points > 0),
    PRIMARY KEY (assessment_id, position),
    UNIQUE (assessment_id, version_id),
    FOREIGN KEY (assessment_id, owner_id) REFERENCES assessments (id, owner_id),
    FOREIGN KEY (version_id, owner_id) REFERENCES question_versions (id, owner_id)
);
CREATE TABLE reference_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL REFERENCES assessments,
    code_digest text NOT NULL UNIQUE CHECK (code_digest ~ '^[0-9a-f]{64}$'),
    expires_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at IS NULL OR expires_at > created_at)
);
CREATE TABLE attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    student_id uuid NOT NULL REFERENCES users,
    attempt_number integer NOT NULL CHECK (attempt_number > 0),
    state text NOT NULL DEFAULT 'in_progress' CHECK (state IN ('in_progress','submitted','expired')),
    idempotency_key uuid NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    submitted_at timestamptz,
    FOREIGN KEY (assessment_id, owner_id) REFERENCES assessments (id, owner_id),
    UNIQUE (assessment_id, student_id, attempt_number),
    UNIQUE (student_id, idempotency_key),
    UNIQUE (id, assessment_id, owner_id),
    UNIQUE (id, student_id),
    CHECK ((state = 'in_progress' AND submitted_at IS NULL) OR
           (state <> 'in_progress' AND submitted_at IS NOT NULL AND submitted_at >= started_at))
);
CREATE TABLE attempt_items (
    attempt_id uuid NOT NULL,
    assessment_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    position integer NOT NULL CHECK (position > 0),
    version_id uuid NOT NULL,
    points numeric(8,2) NOT NULL CHECK (points > 0),
    option_order smallint[] NOT NULL DEFAULT ARRAY[0,1,2,3]::smallint[],
    selected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (attempt_id, position),
    UNIQUE (attempt_id, version_id),
    FOREIGN KEY (attempt_id, assessment_id, owner_id) REFERENCES attempts (id, assessment_id, owner_id),
    FOREIGN KEY (version_id, owner_id) REFERENCES question_versions (id, owner_id),
    CHECK (array_ndims(option_order) = 1 AND array_lower(option_order, 1) = 1
           AND cardinality(option_order) = 4 AND option_order @> ARRAY[0,1,2,3]::smallint[])
);
CREATE TABLE answers (
    attempt_id uuid NOT NULL,
    version_id uuid NOT NULL,
    selected_option smallint,
    response_ms integer CHECK (response_ms >= 0),
    is_correct boolean,
    awarded_points numeric(8,2) CHECK (awarded_points >= 0),
    answered_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (attempt_id, version_id),
    FOREIGN KEY (attempt_id, version_id) REFERENCES attempt_items (attempt_id, version_id),
    FOREIGN KEY (version_id, selected_option) REFERENCES options (version_id, ordinal),
    CHECK ((is_correct IS NULL) = (awarded_points IS NULL))
);
CREATE TABLE feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id uuid NOT NULL,
    version_id uuid NOT NULL,
    student_id uuid NOT NULL,
    category text NOT NULL CHECK (category IN ('wrong_answer','wrong_explanation','ambiguous','poor_wording',
       'weak_distractor','too_easy','too_difficult','duplicate','not_from_material','mathematical_error')),
    comment text CHECK (length(comment) <= 2000),
    state text NOT NULL DEFAULT 'open' CHECK (state IN ('open','reviewing','resolved','dismissed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (attempt_id, student_id) REFERENCES attempts (id, student_id),
    FOREIGN KEY (attempt_id, version_id) REFERENCES attempt_items (attempt_id, version_id),
    UNIQUE (attempt_id, version_id, student_id, category)
);
CREATE TABLE student_profiles (
    user_id uuid PRIMARY KEY REFERENCES users,
    preferred_difficulty text NOT NULL DEFAULT 'easy' CHECK (preferred_difficulty IN ('easy','medium','hard')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE topic_mastery (
    student_id uuid NOT NULL REFERENCES student_profiles,
    topic_id uuid NOT NULL REFERENCES topics,
    mastery numeric(5,4) NOT NULL CHECK (mastery BETWEEN 0 AND 1),
    observations integer NOT NULL DEFAULT 0 CHECK (observations >= 0),
    current_difficulty text NOT NULL DEFAULT 'easy' CHECK (current_difficulty IN ('easy','medium','hard')),
    algorithm_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (student_id, topic_id)
);
CREATE TABLE mastery_evidence (
    student_id uuid NOT NULL REFERENCES student_profiles,
    topic_id uuid NOT NULL,
    attempt_id uuid NOT NULL,
    version_id uuid NOT NULL,
    algorithm_version text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (student_id, attempt_id, version_id),
    FOREIGN KEY (attempt_id, student_id) REFERENCES attempts (id, student_id),
    FOREIGN KEY (attempt_id, version_id) REFERENCES answers (attempt_id, version_id),
    FOREIGN KEY (version_id, topic_id) REFERENCES question_versions (id, topic_id)
);
CREATE TABLE audit_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id uuid REFERENCES users,
    event_type text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid,
    details jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(details) = 'object'),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

-- Immutable content and evidence: corrections are new records/versions.
CREATE FUNCTION deny_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only; create a new version', TG_TABLE_NAME USING ERRCODE = '23514';
END $$;
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['documents','chunks','generation_runs','question_versions','options',
        'question_sources','question_verifications','attempt_items','mastery_evidence','audit_events'] LOOP
        EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON mcq.%I FOR EACH ROW EXECUTE FUNCTION mcq.deny_mutation()', t);
    END LOOP;
END $$;

-- All four options must exist by commit; API inserts version + options in one transaction.
CREATE FUNCTION check_options() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    IF (SELECT count(*) FROM options WHERE version_id = NEW.id) <> 4 THEN
        RAISE EXCEPTION 'A question version requires exactly four options' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER four_options AFTER INSERT ON question_versions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_options();

CREATE FUNCTION check_release() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
DECLARE v question_verifications; q question_versions;
BEGIN
    SELECT * INTO v FROM question_verifications WHERE id = NEW.verification_id AND version_id = NEW.version_id;
    SELECT * INTO q FROM question_versions WHERE id = NEW.version_id;
    IF v.id IS NULL OR v.status <> 'PASS' OR v.blind_option <> q.correct_option
       OR NOT EXISTS (SELECT 1 FROM question_sources WHERE version_id = NEW.version_id)
       OR (q.question_type = 'numerical' AND v.math_result <> 'pass') THEN
        RAISE EXCEPTION 'Release requires matching verification, source evidence and numerical validation' USING ERRCODE = '23514';
    END IF;
    IF NEW.reviewed_by IS NOT NULL AND NEW.reviewed_by <> q.owner_id THEN
        RAISE EXCEPTION 'Reviewer must own this question' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER release_gate BEFORE INSERT OR UPDATE ON question_releases FOR EACH ROW EXECUTE FUNCTION check_release();

CREATE FUNCTION guard_assessment_items() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
DECLARE aid uuid;
BEGIN
    aid := CASE WHEN TG_OP = 'DELETE' THEN OLD.assessment_id ELSE NEW.assessment_id END;
    PERFORM 1 FROM assessments WHERE id = aid AND state = 'draft' FOR UPDATE;
    IF NOT FOUND OR (TG_OP = 'UPDATE' AND NEW.assessment_id <> OLD.assessment_id) THEN
        RAISE EXCEPTION 'Published content is frozen; duplicate into a new assessment' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER freeze_items BEFORE INSERT OR UPDATE OR DELETE ON assessment_questions
    FOR EACH ROW EXECUTE FUNCTION guard_assessment_items();

CREATE FUNCTION guard_assessment() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.state <> 'draft' THEN
        RAISE EXCEPTION 'Create a draft first' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.state <> 'draft' THEN
        IF (to_jsonb(NEW) - 'state') IS DISTINCT FROM (to_jsonb(OLD) - 'state')
           OR NOT (NEW.state = OLD.state OR (OLD.state = 'published' AND NEW.state = 'closed')) THEN
            RAISE EXCEPTION 'Published assessment settings are immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.state = 'draft' AND NEW.state <> 'draft' THEN
        IF NEW.state <> 'published' THEN RAISE EXCEPTION 'Publish before closing' USING ERRCODE = '23514'; END IF;
        IF NEW.kind = 'classroom' AND NOT EXISTS (SELECT 1 FROM user_roles WHERE user_id = NEW.owner_id AND role = 'teacher') THEN
            RAISE EXCEPTION 'Classroom owner must have teacher role' USING ERRCODE = '23514';
        END IF;
        -- Row locks serialize release/quarantine changes with publication.
        PERFORM r.version_id FROM question_releases r JOIN assessment_questions aq ON aq.version_id = r.version_id
            WHERE aq.assessment_id = NEW.id FOR UPDATE OF r;
        IF NEW.mode = 'fixed' AND NOT EXISTS (SELECT 1 FROM assessment_questions WHERE assessment_id = NEW.id) THEN
            RAISE EXCEPTION 'Fixed assessment cannot be empty' USING ERRCODE = '23514';
        END IF;
        IF EXISTS (SELECT 1 FROM assessment_questions aq LEFT JOIN question_releases r USING (version_id)
            WHERE aq.assessment_id = NEW.id AND (r.version_id IS NULL OR r.state <> 'approved'
            OR (NEW.kind = 'classroom' AND r.reviewed_by IS DISTINCT FROM NEW.owner_id))) THEN
            RAISE EXCEPTION 'All published questions require eligible approval' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER assessment_gate BEFORE INSERT OR UPDATE ON assessments FOR EACH ROW EXECUTE FUNCTION guard_assessment();

CREATE FUNCTION check_code() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    PERFORM 1 FROM assessments WHERE id = NEW.assessment_id AND kind = 'classroom' AND state = 'published' FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Codes require a published classroom assessment' USING ERRCODE = '23514'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER code_gate BEFORE INSERT ON reference_codes FOR EACH ROW EXECUTE FUNCTION check_code();

CREATE FUNCTION guard_attempt() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
DECLARE a assessments;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.state <> 'in_progress' OR
           (to_jsonb(NEW) - ARRAY['state','submitted_at']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['state','submitted_at']) THEN
            RAISE EXCEPTION 'Attempt identity and submitted attempt are immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.state = 'submitted' THEN
            SELECT * INTO a FROM assessments WHERE id = NEW.assessment_id;
            IF NOT EXISTS (SELECT 1 FROM attempt_items WHERE attempt_id = NEW.id)
               OR EXISTS (SELECT 1 FROM attempt_items i LEFT JOIN answers ans
                    ON ans.attempt_id = i.attempt_id AND ans.version_id = i.version_id
                    WHERE i.attempt_id = NEW.id AND ans.is_correct IS NULL)
               OR (a.mode = 'fixed' AND EXISTS (SELECT 1 FROM assessment_questions aq
                    WHERE aq.assessment_id = a.id AND NOT EXISTS (SELECT 1 FROM attempt_items i
                    WHERE i.attempt_id = NEW.id AND i.version_id = aq.version_id))) THEN
                RAISE EXCEPTION 'Submission requires every item and a scored answer (including skipped items)' USING ERRCODE = '23514';
            END IF;
        END IF;
        RETURN NEW;
    END IF;
    SELECT * INTO a FROM assessments WHERE id = NEW.assessment_id FOR UPDATE;
    IF a.id IS NULL OR a.state <> 'published' OR NEW.state <> 'in_progress'
       OR NEW.attempt_number > a.max_attempts OR
       (SELECT count(*) FROM attempts WHERE assessment_id = NEW.assessment_id AND student_id = NEW.student_id) >= a.max_attempts THEN
        RAISE EXCEPTION 'Assessment unavailable or attempt limit reached' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM user_roles WHERE user_id = NEW.student_id AND role = 'student') OR
       (a.kind = 'practice' AND a.owner_id <> NEW.student_id) OR
       (a.kind = 'classroom' AND NOT EXISTS (SELECT 1 FROM course_memberships WHERE course_id = a.course_id AND student_id = NEW.student_id AND active)) THEN
        RAISE EXCEPTION 'Student is not eligible for this assessment' USING ERRCODE = '23514';
    END IF;
    PERFORM r.version_id FROM question_releases r JOIN assessment_questions aq ON aq.version_id = r.version_id
        WHERE aq.assessment_id = a.id FOR SHARE OF r;
    IF EXISTS (SELECT 1 FROM assessment_questions aq JOIN question_releases r USING (version_id)
        WHERE aq.assessment_id = a.id AND r.state <> 'approved') THEN
        RAISE EXCEPTION 'Assessment contains quarantined content; new attempts are paused' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER attempt_gate BEFORE INSERT OR UPDATE ON attempts FOR EACH ROW EXECUTE FUNCTION guard_attempt();

CREATE FUNCTION check_attempt_item() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
DECLARE a assessments;
BEGIN
    PERFORM 1 FROM attempts WHERE id = NEW.attempt_id AND state = 'in_progress' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Attempt is not open' USING ERRCODE = '23514'; END IF;
    SELECT * INTO a FROM assessments WHERE id = NEW.assessment_id;
    PERFORM 1 FROM question_releases WHERE version_id = NEW.version_id AND state = 'approved' FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Newly presented item must remain approved' USING ERRCODE = '23514'; END IF;
    IF a.mode = 'fixed' THEN
        IF NOT EXISTS (SELECT 1 FROM assessment_questions WHERE assessment_id = a.id
            AND version_id = NEW.version_id AND points = NEW.points) THEN
            RAISE EXCEPTION 'Item is not in the fixed published snapshot' USING ERRCODE = '23514';
        END IF;
    ELSE
        PERFORM 1 FROM question_releases WHERE version_id = NEW.version_id AND state = 'approved' FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Adaptive item is not approved' USING ERRCODE = '23514'; END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER attempt_item_gate BEFORE INSERT ON attempt_items FOR EACH ROW EXECUTE FUNCTION check_attempt_item();

CREATE FUNCTION guard_answer() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
DECLARE aid uuid; vid uuid; max_points numeric; expected_correct boolean;
BEGIN
    aid := CASE WHEN TG_OP = 'DELETE' THEN OLD.attempt_id ELSE NEW.attempt_id END;
    vid := CASE WHEN TG_OP = 'DELETE' THEN OLD.version_id ELSE NEW.version_id END;
    PERFORM 1 FROM attempts WHERE id = aid AND state = 'in_progress' FOR UPDATE;
    IF NOT FOUND OR (TG_OP = 'UPDATE' AND (NEW.attempt_id, NEW.version_id) IS DISTINCT FROM (OLD.attempt_id, OLD.version_id)) THEN
        RAISE EXCEPTION 'Answer is frozen or identity changed' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    SELECT points INTO max_points FROM attempt_items WHERE attempt_id = aid AND version_id = vid;
    IF NEW.awarded_points > max_points THEN RAISE EXCEPTION 'Score exceeds item points' USING ERRCODE = '23514'; END IF;
    SELECT coalesce(NEW.selected_option = correct_option, false) INTO expected_correct FROM question_versions WHERE id = vid;
    IF NEW.is_correct IS NOT NULL AND (NEW.is_correct IS DISTINCT FROM expected_correct OR
        NEW.awarded_points IS DISTINCT FROM CASE WHEN expected_correct THEN max_points ELSE 0 END) THEN
        RAISE EXCEPTION 'Scoring must match the stored key and item points' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER answer_gate BEFORE INSERT OR UPDATE OR DELETE ON answers FOR EACH ROW EXECUTE FUNCTION guard_answer();

CREATE FUNCTION check_mastery_evidence() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM attempts a JOIN answers ans ON ans.attempt_id = a.id
        WHERE a.id = NEW.attempt_id AND a.state = 'submitted' AND ans.version_id = NEW.version_id AND ans.is_correct IS NOT NULL) THEN
        RAISE EXCEPTION 'Mastery needs a submitted, scored answer' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER mastery_gate BEFORE INSERT ON mastery_evidence FOR EACH ROW EXECUTE FUNCTION check_mastery_evidence();

CREATE TRIGGER preserve_attempt BEFORE DELETE ON attempts FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER preserve_release BEFORE DELETE ON question_releases FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE FUNCTION seal_sources() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    PERFORM 1 FROM question_versions WHERE id = NEW.version_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM question_verifications WHERE version_id = NEW.version_id) THEN
        RAISE EXCEPTION 'Source evidence must be complete before verification' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER source_gate BEFORE INSERT ON question_sources FOR EACH ROW EXECUTE FUNCTION seal_sources();
CREATE FUNCTION lock_verification_version() RETURNS trigger LANGUAGE plpgsql SET search_path = mcq, public AS $$
BEGIN
    PERFORM 1 FROM question_versions WHERE id = NEW.version_id FOR UPDATE;
    RETURN NEW;
END $$;
CREATE TRIGGER verification_version_lock BEFORE INSERT ON question_verifications
    FOR EACH ROW EXECUTE FUNCTION lock_verification_version();
CREATE FUNCTION guard_code() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - ARRAY['expires_at','revoked_at']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['expires_at','revoked_at']) THEN
        RAISE EXCEPTION 'Code identity is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER code_identity BEFORE UPDATE ON reference_codes FOR EACH ROW EXECUTE FUNCTION guard_code();

CREATE INDEX materials_owner_idx ON materials (owner_id, created_at);
CREATE INDEX topics_course_idx ON topics (course_id);
CREATE INDEX versions_topic_idx ON question_versions (topic_id, difficulty);
CREATE INDEX sources_chunk_idx ON question_sources (chunk_id);
CREATE INDEX verifications_version_idx ON question_verifications (version_id, created_at);
CREATE INDEX assessments_owner_idx ON assessments (owner_id, created_at);
CREATE INDEX attempts_student_idx ON attempts (student_id, started_at);
CREATE INDEX feedback_queue_idx ON feedback (state, created_at);
CREATE INDEX feedback_version_idx ON feedback (version_id, category);
CREATE INDEX audit_entity_idx ON audit_events (entity_type, entity_id, occurred_at);

-- Derived analytics avoid a second, inconsistent scores table. Server controls visibility.
CREATE VIEW attempt_scores AS
SELECT a.id AS attempt_id, a.student_id, a.assessment_id, a.state,
       count(i.version_id) AS item_count, coalesce(sum(i.points),0) AS possible_points,
       coalesce(sum(ans.awarded_points),0) AS awarded_points,
       count(ans.is_correct) AS scored_items
FROM attempts a LEFT JOIN attempt_items i ON i.attempt_id = a.id
LEFT JOIN answers ans ON ans.attempt_id = i.attempt_id AND ans.version_id = i.version_id
GROUP BY a.id;
REVOKE ALL ON ALL TABLES IN SCHEMA mcq FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA mcq FROM PUBLIC;
