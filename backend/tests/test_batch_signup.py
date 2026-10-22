"""Workflow tests use synthetic inference, never claim model-quality evidence."""
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.auth.security import AuthError
from backend.app.generator.mock import generate_mock
from backend.app.generator.schemas import GenerateRequest
from backend.app.rag.encoder import LocalEncoder
from backend.tests.test_generator import payload, source
from backend.tests.test_materials import pdf_bytes
from backend.tests.test_rag import FakeEncoder
from backend.tests.test_student import integration, students  # noqa: F401


def test_ai_launcher_refuses_missing_weights_without_loading(monkeypatch, tmp_path):
    from deployment import ai

    monkeypatch.setattr(ai, 'snapshot', lambda: {'available_ram_gib': 0.4})
    monkeypatch.setattr(ai, 'executable', lambda: pytest.fail('runtime must not launch'))
    monkeypatch.setattr(ai, 'ROOT', tmp_path)
    with pytest.raises(ai.OperationError, match='not installed'):
        ai.prerequisites()


@pytest.mark.parametrize("count", [9, 31, 0])
def test_batch_count_rejected(count):
    with pytest.raises(ValidationError):
        GenerateRequest(**payload(batch_id=uuid4(), batch_count=count))


def test_batch_index_and_identity_required():
    for extra in ({"batch_count": 10}, {"batch_id": uuid4()},
                  {"batch_id": uuid4(), "batch_count": 10, "batch_index": 10}):
        with pytest.raises(ValidationError):
            GenerateRequest(**payload(**extra))
    assert GenerateRequest(**payload(batch_id=uuid4(), batch_count=30, batch_index=29)).batch_count == 30


def test_embedding_low_memory_does_not_launch_worker(monkeypatch):
    encoder = LocalEncoder()
    monkeypatch.setattr(encoder, "available", lambda: True)
    monkeypatch.setattr("backend.app.rag.encoder.snapshot", lambda: {"available_ram_gib": 0.4})
    monkeypatch.setattr("backend.app.rag.encoder.subprocess.run", lambda *a, **k: pytest.fail("worker launched"))
    with pytest.raises(AuthError) as error:
        encoder.encode(["A source sentence"])
    assert error.value.code == "EMBEDDING_LOW_MEMORY"


@integration
def test_teacher_signup_login_ownership_and_no_student_promotion(request):
    client, app, ids, tokens = request.getfixturevalue("students")
    data = {"email": "new-teacher@example.com", "display_name": "Teacher fixture", "password": "Teacher fixture 42!"}
    response = client.post('/api/v1/auth/register-teacher', json=data)
    assert response.status_code == 201, response.text
    assert response.json()['roles'] == ['teacher']
    login = client.post('/api/v1/auth/login', json={k: data[k] for k in ('email', 'password')})
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    assert client.get('/api/v1/teacher/dashboard', headers=headers).status_code == 200
    assert client.get('/api/v1/roles/student', headers=headers).status_code == 403
    assert client.get('/api/v1/teacher/dashboard', headers=tokens[0]).status_code == 403
    conflict = client.post('/api/v1/auth/register-teacher', json={**data, 'email': 'student0@example.com'})
    assert conflict.status_code == 409
    assert client.get('/api/v1/auth/me', headers=tokens[0]).json()['roles'] == ['student']
    assert client.post('/api/v1/auth/register-teacher', json={**data, 'role': 'admin'}).status_code == 422
    with app.state.database.session() as session:
        assert not session.execute(text("SELECT has_table_privilege(current_user,'mcq.user_roles','INSERT')")).scalar_one()


@integration
def test_batch_rag_persistence_retry_duplicates_and_mock_gate(request, tmp_path, monkeypatch):
    client, app, ids, tokens = request.getfixturevalue("students")
    app.state.materials.root = tmp_path / 'uploads'
    app.state.rag.encoder = FakeEncoder()
    uploaded = client.post('/api/v1/materials?title=Batch', content=pdf_bytes(('Normalization reduces redundant data.',)), headers={**tokens[0], 'Content-Type': 'application/pdf'})
    assert uploaded.status_code == 201
    material = uploaded.json()['id']
    assert client.post(f'/api/v1/rag/materials/{material}/index', headers=tokens[0]).status_code == 200
    body = payload(material_ids=[material], batch_id=str(uuid4()), batch_count=10)
    assert client.post('/api/v1/generator/drafts', json=body, headers=tokens[0]).json()['error']['code'] == 'GENERATOR_REAL_REQUIRED'
    generator = app.state.generator
    generator.settings = generator.settings.model_copy(update={'generator_mode': 'ollama'})
    monkeypatch.setattr(generator.client, 'inspect', lambda: {})
    calls = []
    def inference(prompt, tokens, *, seed):
        calls.append(seed)
        result = generate_mock(source())
        result.question.stem = f'Which property of normalization is described in fixture {seed}?'
        return result, {'model': 'synthetic-inference', 'digest': 'a' * 64}
    monkeypatch.setattr(generator.client, 'generate', inference)
    first = client.post('/api/v1/generator/drafts', json=body, headers=tokens[0])
    assert first.status_code == 200, first.text
    assert client.post('/api/v1/generator/drafts', json=body, headers=tokens[0]).json()['id'] == first.json()['id']
    assert calls == [42]
    for i in range(1, 10):
        item = client.post('/api/v1/generator/drafts', json={**body, 'batch_index': i, 'idempotency_key': str(uuid4())}, headers=tokens[0])
        assert item.status_code == 200, item.text
    assert calls == list(range(42, 52))
    duplicate = client.post('/api/v1/generator/drafts', json={**body, 'idempotency_key': str(uuid4())}, headers=tokens[0])
    assert duplicate.status_code == 422
    assert duplicate.json()['error']['code'] == 'GENERATOR_DUPLICATE'
    assert client.get('/api/v1/generator/drafts?offset=0&limit=20', headers=tokens[0]).json()['total'] == 10
    assert client.get('/api/v1/generator/drafts/' + first.json()['id'], headers=tokens[1]).status_code == 404
