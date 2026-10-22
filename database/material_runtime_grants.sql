-- Apply as trusted database operator: psql ... -v runtime_role=adaptive_mcq_app -f database/material_runtime_grants.sql
-- FREE / OPEN SOURCE local PostgreSQL. No UPDATE/DELETE of immutable provenance.
GRANT SELECT ON mcq.materials, mcq.documents, mcq.chunks TO :"runtime_role";
GRANT INSERT (owner_id,title) ON mcq.materials TO :"runtime_role";
GRANT INSERT (material_id,owner_id,version,storage_key,sha256,byte_size,page_count) ON mcq.documents TO :"runtime_role";
GRANT INSERT (document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version) ON mcq.chunks TO :"runtime_role";
