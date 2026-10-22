import json
from collections import OrderedDict
from hashlib import sha256
from threading import RLock

from sqlalchemy import bindparam, text

from .encoder import LocalEncoder, fail, validate_vectors


def pack_sources(rows, top_k, char_limit):
    sources, seen, used = [], set(), 0
    for row in rows:
        if row["content_sha256"] in seen:
            continue
        remaining = char_limit - used
        if remaining < 100 or len(sources) == top_k:
            break
        excerpt = row["content"][: min(1200, remaining)]
        used += len(excerpt)
        seen.add(row["content_sha256"])
        sources.append(
            {
                key: row[key]
                for key in (
                    "material_id",
                    "title",
                    "document_id",
                    "chunk_id",
                    "page_start",
                    "page_end",
                    "content_sha256",
                )
            }
            | {
                "citation": f"S{len(sources) + 1}",
                "similarity": round(max(-1, min(1, row["similarity"])), 6),
                "excerpt": excerpt,
                "clipped": len(excerpt) < len(row["content"]),
                "excerpt_sha256": sha256(excerpt.encode()).hexdigest(),
            }
        )
    return sources, used


class RagService:
    def __init__(self, database, settings, encoder=None):
        self.database, self.settings = database, settings
        self.encoder = encoder or LocalEncoder()
        self.gate = RLock()
        # Cache only tiny query vectors, never a resident model or search results.
        # Ownership and current document state are still checked on every search.
        self.query_vectors = OrderedDict()

    def owned(self, session, owner, material):
        document = session.execute(
            text("""
            SELECT d.id FROM mcq.documents d JOIN mcq.materials m ON m.id=d.material_id
            WHERE m.id=:material AND m.owner_id=:owner AND d.owner_id=:owner
            AND NOT m.archived AND d.version=1
        """),
            {"owner": owner, "material": material},
        ).scalar_one_or_none()
        if document is None:
            raise fail("MATERIAL_NOT_FOUND", 404)
        return document

    def model_id(self, session):
        return session.execute(
            text(
                "SELECT id FROM mcq.embedding_models WHERE model_name=:model AND revision=:revision"
            ),
            {"model": self.encoder.model_name, "revision": self.encoder.revision},
        ).scalar_one_or_none()

    def status(self, owner, material):
        with self.database.session() as session:
            document = self.owned(session, owner, material)
            model = self.model_id(session)
            counts = (
                session.execute(
                    text("""
                SELECT count(*) AS chunks, count(e.chunk_id) AS indexed FROM mcq.chunks c
                LEFT JOIN mcq.embeddings e ON e.chunk_id=c.id AND e.owner_id=:owner AND e.model_id=:model
                WHERE c.document_id=:document AND c.owner_id=:owner
            """),
                    {"document": document, "owner": owner, "model": model},
                )
                .mappings()
                .one()
            )
        return {
            "material_id": material,
            **counts,
            "state": "ready"
            if counts["chunks"] and counts["chunks"] == counts["indexed"]
            else "partial"
            if counts["indexed"]
            else "not_indexed",
            "model_available": self.encoder.available(),
            "model": self.encoder.model_name,
            "revision": self.encoder.revision,
        }

    def index(self, owner, material):
        current = self.status(owner, material)
        if current["state"] == "ready":
            return current
        if not self.gate.acquire(blocking=False):
            raise fail("RAG_BUSY", 409)
        try:
            with self.database.session() as session:
                document = self.owned(session, owner, material)
                model = self.model_id(session)
                chunks = (
                    session.execute(
                        text("""
                    SELECT c.id,c.content FROM mcq.chunks c
                    WHERE c.document_id=:document AND c.owner_id=:owner
                    AND NOT EXISTS(SELECT 1 FROM mcq.embeddings e WHERE e.chunk_id=c.id AND e.model_id=:model)
                    ORDER BY c.ordinal LIMIT 501
                """),
                        {"document": document, "owner": owner, "model": model},
                    )
                    .mappings()
                    .all()
                )
            if not 1 <= len(chunks) <= 500:
                raise fail("RAG_CHUNK_LIMIT", 422)
            vectors = validate_vectors(
                self.encoder.encode([c["content"] for c in chunks]), len(chunks)
            )
            with self.database.session() as session, session.begin():
                self.owned(session, owner, material)
                session.execute(
                    text(
                        "INSERT INTO mcq.embedding_models(model_name,revision,dimension,normalization) VALUES(:model,:revision,384,'l2') ON CONFLICT (model_name,revision) DO NOTHING"
                    ),
                    {"model": self.encoder.model_name, "revision": self.encoder.revision},
                )
                model = self.model_id(session)
                session.execute(
                    text("""
                    INSERT INTO mcq.embeddings(chunk_id,owner_id,model_id,embedding)
                    VALUES(:chunk,:owner,:model,CAST(:vector AS public.vector))
                    ON CONFLICT(chunk_id,model_id) DO NOTHING
                """),
                    [
                        {
                            "chunk": chunk["id"],
                            "owner": owner,
                            "model": model,
                            "vector": json.dumps(vector),
                        }
                        for chunk, vector in zip(chunks, vectors, strict=True)
                    ],
                )
                session.execute(
                    text(
                        "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,'material.indexed','material',:material)"
                    ),
                    {"owner": owner, "material": material},
                )
            return self.status(owner, material)
        finally:
            self.gate.release()

    def search(self, owner, payload):
        for material in payload.material_ids:
            status = self.status(owner, material)
            if status["state"] != "ready":
                raise fail("RAG_NOT_INDEXED", 409)
        if not self.gate.acquire(blocking=False):
            raise fail("RAG_BUSY", 409)
        try:
            key = (str(owner), self.encoder.model_name, self.encoder.revision, sha256(payload.query.encode()).hexdigest())
            vector = self.query_vectors.get(key)
            if vector is None:
                vector = validate_vectors(self.encoder.encode([payload.query]), 1)[0]
                self.query_vectors[key] = vector
                if len(self.query_vectors) > 32:
                    self.query_vectors.popitem(last=False)
            self.query_vectors.move_to_end(key)
            with self.database.session() as session:
                model = self.model_id(session)
                query = text("""
                    SELECT c.id AS chunk_id,c.document_id,d.material_id,m.title,c.page_start,c.page_end,
                           c.content,c.content_sha256,1-(e.embedding <=> CAST(:vector AS public.vector)) AS similarity
                    FROM mcq.embeddings e JOIN mcq.chunks c ON c.id=e.chunk_id AND c.owner_id=e.owner_id
                    JOIN mcq.documents d ON d.id=c.document_id AND d.owner_id=c.owner_id
                    JOIN mcq.materials m ON m.id=d.material_id AND m.owner_id=d.owner_id
                    WHERE e.owner_id=:owner AND e.model_id=:model AND m.id IN :materials
                    AND NOT m.archived AND d.version=1
                    AND 1-(e.embedding <=> CAST(:vector AS public.vector)) >= :threshold
                    ORDER BY e.embedding <=> CAST(:vector AS public.vector),c.id LIMIT :limit
                """).bindparams(bindparam("materials", expanding=True))
                rows = (
                    session.execute(
                        query,
                        {
                            "owner": owner,
                            "model": model,
                            "vector": json.dumps(vector),
                            "materials": payload.material_ids,
                            "threshold": self.settings.rag_min_similarity,
                            "limit": self.settings.rag_top_k * 8,
                        },
                    )
                    .mappings()
                    .all()
                )
            sources, used = pack_sources(
                rows, self.settings.rag_top_k, self.settings.rag_context_chars
            )
            return {
                "status": "sources_found" if sources else "insufficient_evidence",
                "sources": sources,
                "excerpt_char_count": used,
                "excerpt_char_limit": self.settings.rag_context_chars,
                "model": self.encoder.model_name,
                "revision": self.encoder.revision,
                "threshold": self.settings.rag_min_similarity,
            }
        finally:
            self.gate.release()
