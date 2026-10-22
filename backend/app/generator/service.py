import json
import re
from hashlib import sha256

from sqlalchemy import bindparam, text

from ..auth.security import AuthError
from ..hardware import snapshot
from ..rag.schemas import SearchRequest
from ..rag.service import pack_sources
from .client import OllamaGenerator, fail
from .mock import generate_mock
from .prompt import PROMPT_VERSION, build_prompt, tokenizer


class GeneratorService:
    def __init__(self, database, settings, rag):
        self.database, self.settings, self.rag = database, settings, rag
        self.client = OllamaGenerator(settings)

    def status(self):
        mode = self.settings.generator_mode
        result = {
            "mode": mode,
            "ready": mode == "mock",
            "hardware": snapshot(),
            "selection_status": "Hardware-validated model selection: pending",
            "model": self.settings.generator_model,
            "error_code": None,
        }
        if mode == "ollama":
            try:
                info = self.client.inspect()
                tokenizer()
                result.update(ready=True, hardware=info["hardware"])
            except AuthError as error:
                result["error_code"] = error.code
        return result

    def mock_sources(self, owner, payload):
        # Lightweight test retrieval only. Real semantic RAG remains a separate
        # route and is used by the Ollama adapter; no embeddings run in mock mode.
        words = set(re.findall(r"\w+", payload.topic.lower()))
        with self.database.session() as session:
            for material in payload.material_ids:
                self.rag.owned(session, owner, material)
            query = text("""
                SELECT c.id AS chunk_id,c.document_id,d.material_id,m.title,c.page_start,c.page_end,
                       c.content,c.content_sha256
                FROM mcq.chunks c JOIN mcq.documents d ON d.id=c.document_id AND d.owner_id=c.owner_id
                JOIN mcq.materials m ON m.id=d.material_id AND m.owner_id=d.owner_id
                WHERE c.owner_id=:owner AND m.id IN :materials AND NOT m.archived AND d.version=1
                ORDER BY m.id,c.ordinal LIMIT 1500
            """).bindparams(bindparam("materials", expanding=True))
            rows = (
                session.execute(query, {"owner": owner, "materials": payload.material_ids})
                .mappings()
                .all()
            )
        ranked = []
        for row in rows:
            overlap = len(words & set(re.findall(r"\w+", row["content"].lower())))
            if overlap:
                ranked.append({**row, "similarity": overlap / max(len(words), 1)})
        ranked.sort(key=lambda row: -row["similarity"])
        return pack_sources(ranked, 1, 1200)[0]

    def existing(self, session, owner, key, fingerprint):
        row = (
            session.execute(
                text("""
            SELECT j.parameters,v.id FROM mcq.jobs j
            JOIN mcq.generation_runs g ON g.job_id=j.id AND g.owner_id=j.owner_id
            JOIN mcq.question_versions v ON v.generation_run_id=g.id AND v.owner_id=g.owner_id
            WHERE j.owner_id=:owner AND j.kind='generate' AND j.idempotency_key=:key AND v.version=1
        """),
                {"owner": owner, "key": key},
            )
            .mappings()
            .one_or_none()
        )
        if row and row["parameters"].get("fingerprint") != fingerprint:
            raise fail("GENERATOR_KEY_CONFLICT", 409)
        return row["id"] if row else None

    def generate(self, owner, payload):
        mode = self.settings.generator_mode
        if mode == "disabled":
            raise fail("GENERATOR_DISABLED")
        if payload.batch_count is not None and mode != "ollama":
            raise fail("GENERATOR_REAL_REQUIRED", 409)
        parameters = payload.model_dump(mode="json", exclude={"idempotency_key"})
        fingerprint = sha256(
            json.dumps({**parameters, "mode": mode}, sort_keys=True).encode()
        ).hexdigest()
        with self.database.session() as session:
            existing = self.existing(session, owner, payload.idempotency_key, fingerprint)
        if existing:
            return self.get(owner, existing)
        if not self.rag.gate.acquire(blocking=False):
            raise fail("GENERATOR_BUSY", 409)
        try:
            if mode == "mock":
                sources = self.mock_sources(owner, payload)
                if not sources:
                    raise fail("GENERATOR_INSUFFICIENT_EVIDENCE", 422)
                generated = generate_mock(sources[0])
                metadata = {
                    "model": "deterministic-test-fixture",
                    "digest": "not-an-llm",
                    "retrieval": "keyword_test",
                    "prompt_version": "mock-excerpt-v1",
                }
            else:
                self.client.inspect()  # Fail before expensive embedding work.
                found = self.rag.search(
                    owner, SearchRequest(query=payload.topic, material_ids=payload.material_ids)
                )
                if not found["sources"]:
                    raise fail("GENERATOR_INSUFFICIENT_EVIDENCE", 422)
                previous = []
                if payload.batch_id is not None:
                    with self.database.session() as session:
                        previous = session.execute(text("""
                            SELECT v.stem FROM mcq.question_versions v
                            JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.owner_id=v.owner_id
                            WHERE v.owner_id=:owner AND g.settings->'parameters'->>'batch_id'=:batch
                            ORDER BY v.created_at
                        """), {"owner": owner, "batch": str(payload.batch_id)}).scalars().all()
                    # Rotate the highest-relevance passages, not arbitrary document text.
                    shift = payload.batch_index % len(found["sources"])
                    found["sources"] = found["sources"][shift:] + found["sources"][:shift]
                prompt, sources, tokens = build_prompt(
                    payload,
                    found["sources"],
                    self.settings.llm_context_tokens,
                    self.settings.llm_output_tokens,
                    previous,
                )
                if payload.batch_id is None:
                    generated, metadata = self.client.generate(prompt, tokens)
                else:
                    generated, metadata = self.client.generate(prompt, tokens, seed=42 + payload.batch_index)
                metadata.update(
                    retrieval="semantic",
                    prompt_version=PROMPT_VERSION,
                    context_tokens=self.settings.llm_context_tokens,
                    output_tokens=self.settings.llm_output_tokens,
                    seed=42 + payload.batch_index,
                    temperature=0.2,
                    num_thread=2,
                    num_gpu=0,
                )
            candidate = generated.question
            if generated.status != "draft" or candidate is None:
                raise fail("GENERATOR_INSUFFICIENT_EVIDENCE", 422)
            cited = next(
                (source for source in sources if source["citation"] == candidate.citation), None
            )
            if not cited or candidate.evidence_quote not in cited["excerpt"]:
                raise fail("GENERATOR_EVIDENCE_MISMATCH", 422)
            # Exact substring evidence is not a factual correctness guarantee.
            metadata.update(
                mode=mode,
                sources=sources,
                citation=candidate.citation,
                evidence_quote=candidate.evidence_quote,
                parameters=parameters,
            )
            with self.database.session() as session, session.begin():
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,10))"),
                    {"owner": str(owner)},
                )
                existing = self.existing(session, owner, payload.idempotency_key, fingerprint)
                if existing:
                    version = existing
                else:
                    if payload.batch_id is not None:
                        stems = session.execute(text("""
                            SELECT v.stem FROM mcq.question_versions v
                            JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.owner_id=v.owner_id
                            WHERE v.owner_id=:owner AND g.settings->'parameters'->>'batch_id'=:batch
                        """), {"owner": owner, "batch": str(payload.batch_id)}).scalars().all()
                        def normalize(value):
                            return " ".join(re.findall(r"\w+", value.casefold()))
                        if any(normalize(stem) == normalize(candidate.stem) for stem in stems):
                            raise fail("GENERATOR_DUPLICATE", 422)
                    for material in payload.material_ids:
                        self.rag.owned(session, owner, material)
                    topic = session.execute(
                        text(
                            "SELECT id FROM mcq.topics WHERE owner_id=:owner AND course_id IS NULL AND name=:name"
                        ),
                        {"owner": owner, "name": payload.topic},
                    ).scalar_one_or_none()
                    if topic is None:
                        topic = session.execute(
                            text(
                                "INSERT INTO mcq.topics(owner_id,name) VALUES(:owner,:name) RETURNING id"
                            ),
                            {"owner": owner, "name": payload.topic},
                        ).scalar_one()
                    job = session.execute(
                        text("""INSERT INTO mcq.jobs(owner_id,kind,state,idempotency_key,parameters,stage,attempts)
                        VALUES(:owner,'generate','completed',:key,CAST(:parameters AS jsonb),'private_draft_saved',1) RETURNING id"""),
                        {
                            "owner": owner,
                            "key": payload.idempotency_key,
                            "parameters": json.dumps({"fingerprint": fingerprint}),
                        },
                    ).scalar_one()
                    run = session.execute(
                        text("""INSERT INTO mcq.generation_runs(owner_id,job_id,generator_model,model_digest,prompt_version,settings)
                        VALUES(:owner,:job,:model,:digest,:prompt,CAST(:settings AS jsonb)) RETURNING id"""),
                        {
                            "owner": owner,
                            "job": job,
                            "model": metadata["model"],
                            "digest": metadata["digest"],
                            "prompt": metadata["prompt_version"],
                            "settings": json.dumps(metadata, default=str),
                        },
                    ).scalar_one()
                    question = session.execute(
                        text("INSERT INTO mcq.questions(owner_id) VALUES(:owner) RETURNING id"),
                        {"owner": owner},
                    ).scalar_one()
                    version = session.execute(
                        text("""INSERT INTO mcq.question_versions(question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type)
                        VALUES(:question,:owner,1,:topic,:run,:stem,:explanation,:answer,:difficulty,:cognitive,'conceptual') RETURNING id"""),
                        {
                            "question": question,
                            "owner": owner,
                            "topic": topic,
                            "run": run,
                            "stem": candidate.stem,
                            "explanation": candidate.explanation,
                            "answer": candidate.correct_option,
                            "difficulty": payload.difficulty,
                            "cognitive": payload.cognitive_level,
                        },
                    ).scalar_one()
                    session.execute(
                        text(
                            "INSERT INTO mcq.options(version_id,ordinal,content) VALUES(:version,:ordinal,:content)"
                        ),
                        [
                            {"version": version, "ordinal": n, "content": option}
                            for n, option in enumerate(candidate.options)
                        ],
                    )
                    session.execute(
                        text(
                            "INSERT INTO mcq.question_sources(version_id,chunk_id,owner_id,evidence_quote) VALUES(:version,:chunk,:owner,:quote)"
                        ),
                        {
                            "version": version,
                            "chunk": cited["chunk_id"],
                            "owner": owner,
                            "quote": candidate.evidence_quote,
                        },
                    )
                    session.execute(
                        text(
                            "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,'generation.draft_created','question_version',:version)"
                        ),
                        {"owner": owner, "version": version},
                    )
            return self.get(owner, version)
        finally:
            self.rag.gate.release()

    def get(self, owner, version, *, include_released=False):
        with self.database.session() as session:
            row = (
                session.execute(
                    text("""SELECT v.id,v.stem,v.explanation,v.correct_option,v.difficulty,v.cognitive_level,v.created_at,t.name AS topic,g.settings
                FROM mcq.question_versions v JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.owner_id=v.owner_id
                JOIN mcq.topics t ON t.id=v.topic_id AND t.owner_id=v.owner_id
                WHERE v.owner_id=:owner AND v.id=:version AND (:include_released OR NOT EXISTS(SELECT 1 FROM mcq.question_releases r WHERE r.version_id=v.id))
            """),
                    {"owner": owner, "version": version, "include_released": include_released},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise fail("GENERATOR_DRAFT_NOT_FOUND", 404)
            options = (
                session.execute(
                    text(
                        "SELECT content FROM mcq.options WHERE version_id=:version ORDER BY ordinal"
                    ),
                    {"version": version},
                )
                .scalars()
                .all()
            )
        metadata = row["settings"]
        source = next(s for s in metadata["sources"] if s["citation"] == metadata["citation"])
        return {key: value for key, value in row.items() if key != "settings"} | {
            "options": options,
            "mode": metadata["mode"],
            "status": "unverified",
            "model": metadata["model"],
            "retrieval": metadata["retrieval"],
            "source": source,
            "evidence_quote": metadata["evidence_quote"],
        }

    def list(self, owner, offset, limit):
        with self.database.session() as session:
            clause = """FROM mcq.question_versions v JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.owner_id=v.owner_id
                JOIN mcq.topics t ON t.id=v.topic_id AND t.owner_id=v.owner_id
                WHERE v.owner_id=:owner AND NOT EXISTS(SELECT 1 FROM mcq.question_releases r WHERE r.version_id=v.id)
                AND NOT EXISTS(SELECT 1 FROM mcq.question_versions newer WHERE newer.question_id=v.question_id AND newer.version>v.version)"""
            total = session.execute(
                text("SELECT count(*) " + clause), {"owner": owner}
            ).scalar_one()
            rows = (
                session.execute(
                    text(
                        "SELECT v.id,v.stem,v.created_at,t.name AS topic,g.settings->>'mode' AS mode "
                        + clause
                        + " ORDER BY v.created_at DESC,v.id DESC LIMIT :limit OFFSET :offset"
                    ),
                    {"owner": owner, "limit": limit, "offset": offset},
                )
                .mappings()
                .all()
            )
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "offset": offset,
            "limit": limit,
        }
