import json
import os
import subprocess
import sys
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.auth.security import AuthError
from backend.app.rag.encoder import LocalEncoder, validate_vectors
from backend.app.rag.model_files import (
    COMMIT,
    FILES,
    MODEL_DIR,
    MODEL_NAME,
    REVISION,
    verify_snapshot,
)
from backend.app.rag.schemas import SearchRequest
from backend.app.rag.service import pack_sources
from backend.tests.test_materials import pdf_bytes
from backend.tests.test_student import integration, operator, students  # noqa: F401


class FakeEncoder:
    """Synthetic orthogonal vectors exercise SQL, not semantic model quality."""

    model_name, revision = MODEL_NAME, REVISION
    calls = 0

    def available(self):
        return True

    def encode(self, texts):
        self.calls += 1
        vectors = []
        for value in texts:
            vector = [0.0] * 384
            vector[
                0 if "normal" in value.lower() else 1 if "transaction" in value.lower() else 2
            ] = 1.0
            vectors.append(vector)
        return vectors


@pytest.mark.parametrize(
    "payload",
    [
        {"query": " ", "material_ids": [str(uuid4())]},
        {"query": "test", "material_ids": []},
        {"query": "test", "material_ids": [str(uuid4())] * 2},
        {"query": "test", "material_ids": [str(uuid4()) for _ in range(6)]},
        {"query": "test", "material_ids": [str(uuid4())], "owner_id": str(uuid4())},
    ],
)
def test_search_contract_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        SearchRequest(**payload)


@pytest.mark.parametrize(
    "vectors", [None, [], [[0.0] * 384], [[1.0] * 383], [[float("nan")] * 384], [[1.0] * 384]]
)
def test_vectors_must_be_finite_normalized_and_384_dimensional(vectors):
    with pytest.raises(AuthError):
        validate_vectors(vectors, 1)


def test_context_budget_deduplication_and_provenance():
    def row(content):
        return {
            "material_id": uuid4(),
            "document_id": uuid4(),
            "chunk_id": uuid4(),
            "title": "Source",
            "page_start": 2,
            "page_end": 2,
            "content": content,
            "content_sha256": sha256(content.encode()).hexdigest(),
            "similarity": 0.8,
        }

    first, second = row("a" * 1000), row("b" * 1000)
    sources, used = pack_sources([first, first, second], 3, 1400)
    assert used == 1400 and len(sources) == 2
    assert sources[1]["clipped"] and sources[1]["excerpt"] == "b" * 400
    assert sources[1]["content_sha256"] == second["content_sha256"]
    assert sources[1]["excerpt_sha256"] == sha256(("b" * 400).encode()).hexdigest()
    assert sources[1]["citation"] == "S2" and sources[1]["page_start"] == 2
    assert pack_sources([], 3, 1400) == ([], 0)


def test_snapshot_rejects_missing_corrupt_and_wrong_revision(tmp_path):
    with pytest.raises(OSError):
        verify_snapshot(tmp_path)
    hashes = {}
    for name in FILES:
        file = tmp_path / name
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_bytes(b"fixture")
        hashes[name] = sha256(b"fixture").hexdigest()
    manifest = {"model": MODEL_NAME, "commit": COMMIT, "files": hashes}
    (tmp_path / "snapshot.json").write_text(json.dumps(manifest))
    verify_snapshot(tmp_path)
    (tmp_path / "model.safetensors").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Corrupt"):
        verify_snapshot(tmp_path)
    manifest["commit"] = "wrong"
    (tmp_path / "snapshot.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Invalid"):
        verify_snapshot(tmp_path)


@pytest.mark.integration
@integration
def test_rag_index_search_ownership_filtering_and_revision(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("students")
    app.state.materials.root = tmp_path / "uploads"
    encoder = FakeEncoder()
    app.state.rag.encoder = encoder

    def upload(owner, title, pages):
        response = client.post(
            "/api/v1/materials",
            params={"title": title},
            headers={**tokens[owner], "Content-Type": "application/pdf"},
            content=pdf_bytes(pages),
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    mid = upload(
        0, "Source A", ("Normalization removes duplicate data.", "Transactions are atomic.")
    )
    excluded = upload(0, "Unselected source", ("Normalization in an unselected document.",))
    private = upload(1, "Private other user", ("Normalization in a private document.",))
    path = f"/api/v1/rag/materials/{mid}"
    assert client.get(path).status_code == 401
    status = client.get(path, headers=tokens[0])
    assert status.json()["state"] == "not_indexed"
    assert status.headers["cache-control"] == "no-store"
    payload = {"query": "normalization", "material_ids": [mid]}
    assert client.post("/api/v1/rag/search", json=payload, headers=tokens[0]).status_code == 409
    assert client.post(path + "/index", headers=tokens[1]).status_code == 404
    assert encoder.calls == 0
    for owner, material in [(0, mid), (0, excluded), (1, private)]:
        response = client.post(f"/api/v1/rag/materials/{material}/index", headers=tokens[owner])
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "ready"
    assert encoder.calls == 3
    assert client.post(path + "/index", headers=tokens[0]).json()["indexed"] == 2
    assert encoder.calls == 3
    result = client.post("/api/v1/rag/search", json=payload, headers=tokens[0])
    assert result.status_code == 200, result.text
    sources = result.json()["sources"]
    assert len(sources) == 1 and sources[0]["material_id"] == mid and sources[0]["page_start"] == 1
    assert sources[0]["similarity"] == 1.0
    before_repeat = encoder.calls
    repeated = client.post("/api/v1/rag/search", json=payload, headers=tokens[0])
    assert repeated.json() == result.json()
    assert encoder.calls == before_repeat  # No model reload for the next batch item.
    assert (
        client.post(
            "/api/v1/rag/search", json={**payload, "query": "photosynthesis"}, headers=tokens[0]
        ).json()["status"]
        == "insufficient_evidence"
    )
    calls = encoder.calls
    for materials in [[mid, private], [private]]:
        assert (
            client.post(
                "/api/v1/rag/search", json={**payload, "material_ids": materials}, headers=tokens[0]
            ).status_code
            == 404
        )
    assert encoder.calls == calls
    with app.state.database.session() as session:
        assert session.execute(text("SELECT count(*) FROM mcq.embeddings")).scalar_one() == 4
        assert not session.execute(
            text("SELECT has_table_privilege(current_user,'mcq.embeddings','UPDATE,DELETE')")
        ).scalar_one()
    encoder.revision = "different-fixture-revision"
    assert client.get(path, headers=tokens[0]).json()["indexed"] == 0
    assert client.post("/api/v1/rag/search", json=payload, headers=tokens[0]).status_code == 409
    encoder.revision = REVISION
    app.state.rag.gate.acquire()
    try:
        assert (
            client.post("/api/v1/rag/search", json=payload, headers=tokens[0]).json()["error"][
                "code"
            ]
            == "RAG_BUSY"
        )
    finally:
        app.state.rag.gate.release()
    # Archived documents are not searchable even when their vectors exist.
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(text("UPDATE mcq.materials SET archived=true WHERE id=:id"), {"id": mid})
    assert client.get(path, headers=tokens[0]).status_code == 404


def test_missing_encoder_and_worker_timeout(monkeypatch):
    monkeypatch.setattr("backend.app.rag.encoder.snapshot", lambda: {"available_ram_gib": 2})
    encoder = LocalEncoder()
    monkeypatch.setattr(encoder, "available", lambda: False)
    with pytest.raises(AuthError) as error:
        encoder.encode(["test"])
    assert error.value.code == "EMBEDDING_NOT_INSTALLED"
    monkeypatch.setattr(encoder, "available", lambda: True)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 180)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(AuthError) as error:
        encoder.encode(["test"])
    assert error.value.code == "EMBEDDING_TIMEOUT"


@pytest.mark.integration
@integration
def test_failed_encoding_writes_nothing_and_partial_index_resumes(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("students")
    app.state.materials.root = tmp_path / "uploads"
    response = client.post(
        "/api/v1/materials?title=Recovery",
        headers={**tokens[0], "Content-Type": "application/pdf"},
        content=pdf_bytes(("Normalization source", "Transaction source")),
    )
    assert response.status_code == 201
    material = response.json()["id"]
    path = f"/api/v1/rag/materials/{material}"
    encoder = FakeEncoder()
    app.state.rag.encoder = encoder
    encode = encoder.encode
    encoder.encode = lambda values: [[0.0] * 384 for _ in values]
    failed = client.post(path + "/index", headers=tokens[0])
    assert failed.status_code == 503
    assert client.get(path, headers=tokens[0]).json()["indexed"] == 0
    # RLock.locked() is unavailable on Python 3.12. The test thread can acquire
    # only after the failed HTTP worker released the shared compute gate.
    assert app.state.rag.gate.acquire(blocking=False)
    app.state.rag.gate.release()
    encoder.encode = encode
    # Seed one valid vector as a synthetic interrupted older batch. Normal Phase 9
    # batches commit atomically; this exercises safe fill-in of an existing partial index.
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        model = session.execute(
            text(
                "INSERT INTO mcq.embedding_models(model_name,revision,dimension,normalization) VALUES(:model,:revision,384,'l2') RETURNING id"
            ),
            {"model": MODEL_NAME, "revision": REVISION},
        ).scalar_one()
        chunk = session.execute(
            text(
                "SELECT c.id FROM mcq.chunks c JOIN mcq.documents d ON d.id=c.document_id WHERE d.material_id=:material ORDER BY c.ordinal LIMIT 1"
            ),
            {"material": material},
        ).scalar_one()
        session.execute(
            text(
                "INSERT INTO mcq.embeddings(chunk_id,owner_id,model_id,embedding) VALUES(:chunk,:owner,:model,CAST(:vector AS public.vector))"
            ),
            {
                "chunk": chunk,
                "owner": ids[0],
                "model": model,
                "vector": json.dumps([1.0] + [0.0] * 383),
            },
        )
    assert client.get(path, headers=tokens[0]).json()["state"] == "partial"
    assert client.post(path + "/index", headers=tokens[0]).json()["indexed"] == 2
    assert encoder.calls == 1
    assert client.post(path + "/index", headers=tokens[0]).json()["state"] == "ready"
    assert encoder.calls == 1


@pytest.mark.skipif(
    os.getenv("MCQ_RUN_MODEL_TESTS") != "1",
    reason="Requires explicitly prepared local embedding snapshot",
)
def test_real_offline_cpu_model_normalization_semantics_and_long_windows():
    from backend.app.rag import worker

    texts = [
        "Database normalization reduces redundant data.",
        "Normalization removes duplicated data from database tables.",
        "Photosynthesis uses sunlight to produce energy.",
        "Normalization removes redundancy. " * 120,
        "Database normalization reduces redundant data.",
    ]
    result = subprocess.run(
        [sys.executable, worker.__file__],
        input=json.dumps(texts).encode(),
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    vectors = validate_vectors(data.get("vectors"), 5)
    assert vectors[0] == pytest.approx(vectors[4], abs=1e-6)
    assert data["token_counts"][3] > 256 and data["windows"] > 4
    assert sum(a * b for a, b in zip(vectors[0], vectors[1], strict=True)) > sum(
        a * b for a, b in zip(vectors[0], vectors[2], strict=True)
    )
    assert MODEL_DIR.is_dir()
