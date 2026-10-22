from unittest.mock import MagicMock

import psycopg
import pytest
from deployment import ai, native


def test_low_memory_still_allows_preparing_website_without_inference(monkeypatch, tmp_path):
    manifest = tmp_path / 'models/ollama/manifests/registry.ollama.ai/library/qwen2.5/0.5b-instruct-q4_K_M'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{}')
    monkeypatch.setattr(ai, 'ROOT', tmp_path)
    monkeypatch.setattr(ai, 'snapshot', lambda: {'available_ram_gib': 0.2})
    monkeypatch.setattr(ai, 'tokenizer', lambda: None)
    monkeypatch.setattr(ai, 'verify_snapshot', lambda: None)
    monkeypatch.setattr(ai, 'executable', lambda: 'local-ollama')
    assert ai.prerequisites() == 'local-ollama'


def setup_native(monkeypatch, tmp_path):
    (tmp_path / 'cluster').mkdir()
    (tmp_path / 'cluster/postmaster.pid').write_text('stale marker')
    monkeypatch.setattr(native, 'BASE', tmp_path)
    monkeypatch.setattr(native, 'credentials', lambda: {})
    return tmp_path / 'cluster/postmaster.pid'


def test_stale_pid_is_left_for_postgresql_to_validate(monkeypatch, tmp_path):
    marker = setup_native(monkeypatch, tmp_path)
    def offline(*args):
        raise psycopg.OperationalError('connection refused')
    monkeypatch.setattr(native, 'connect', offline)
    calls = []
    monkeypatch.setattr(native, 'run', lambda tool, arguments: calls.append((tool, arguments)))
    native.start()
    assert calls[0][0] == 'pg_ctl' and calls[0][1][-1] == 'start'
    assert marker.read_text() == 'stale marker'


def test_running_foreign_database_is_not_taken_over(monkeypatch, tmp_path):
    setup_native(monkeypatch, tmp_path)
    connection = MagicMock()
    connection.__enter__.return_value.execute.return_value.fetchone.return_value = [str(tmp_path / 'other')]
    monkeypatch.setattr(native, 'connect', lambda config: connection)
    monkeypatch.setattr(native, 'run', lambda *args: pytest.fail('must not start over another database'))
    with pytest.raises(native.OperationError, match='not this project'):
        native.start()
