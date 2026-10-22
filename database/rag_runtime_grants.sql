-- Trusted operator: psql ... -v runtime_role=adaptive_mcq_app -f database/rag_runtime_grants.sql
-- Material read privileges are supplied by material_runtime_grants.sql.
GRANT SELECT ON mcq.embedding_models, mcq.embeddings TO :"runtime_role";
GRANT INSERT (model_name,revision,dimension,normalization) ON mcq.embedding_models TO :"runtime_role";
GRANT INSERT (chunk_id,owner_id,model_id,embedding) ON mcq.embeddings TO :"runtime_role";
