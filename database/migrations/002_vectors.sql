-- pgvector must first be installed in the native PostgreSQL installation.
-- No arrays, remote embedding API, or cloud database substitute is permitted.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
SET LOCAL search_path = mcq, public;
CREATE TABLE embedding_models (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name text NOT NULL,
    revision text NOT NULL,
    dimension integer NOT NULL CHECK (dimension = 384),
    normalization text NOT NULL CHECK (normalization = 'l2'),
    UNIQUE (model_name, revision),
    UNIQUE (id, dimension)
);
CREATE TABLE embeddings (
    chunk_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    model_id uuid NOT NULL,
    dimension integer NOT NULL DEFAULT 384 CHECK (dimension = 384),
    embedding public.vector(384) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, model_id),
    FOREIGN KEY (chunk_id, owner_id) REFERENCES chunks (id, owner_id),
    FOREIGN KEY (model_id, dimension) REFERENCES embedding_models (id, dimension),
    CHECK (public.vector_norm(embedding) BETWEEN 0.999 AND 1.001)
);
CREATE INDEX embeddings_owner_model_idx ON embeddings (owner_id, model_id);
CREATE TRIGGER embedding_model_immutable BEFORE UPDATE OR DELETE ON embedding_models
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER embedding_immutable BEFORE UPDATE OR DELETE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
REVOKE ALL ON embedding_models, embeddings FROM PUBLIC;
COMMENT ON TABLE embeddings IS 'Exact cosine search first. Filter owner + allowed document IDs + model revision before LIMIT. New dimensions require a migration.';
