"""Migration runner checks; these do not substitute for SQL execution tests."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'migrate.py'
spec = importlib.util.spec_from_file_location('migrate', MODULE)
migrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrate)


class MigrationRunnerTests(unittest.TestCase):
    def test_crlf_does_not_change_checksum(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / '001_first.sql'
            p.write_bytes(b'SELECT 1;\nSELECT 2;\n')
            first = migrate.inventory(Path(root))[0][1]
            p.write_bytes(b'SELECT 1;\r\nSELECT 2;\r\n')
            self.assertEqual(first, migrate.inventory(Path(root))[0][1])

    def test_duplicate_or_gapped_numbers_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ['001_first.sql', '003_third.sql']:
                (Path(root) / name).write_text('SELECT 1;')
            with self.assertRaises(ValueError): migrate.inventory(Path(root))

    def test_modified_content_changes_checksum(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / '001_first.sql'
            p.write_text('SELECT 1;')
            first = migrate.inventory(Path(root))[0][1]
            p.write_text('SELECT 2;')
            self.assertNotEqual(first, migrate.inventory(Path(root))[0][1])

    def test_target_bounds(self):
        for target in [0, -1, 999]:
            with self.assertRaises(ValueError): migrate.render(target)

    def test_connection_string_cannot_override_localhost(self):
        args = ['migrate.py', 'apply', '--database', 'host=remote dbname=test', '--user', 'owner']
        with patch.object(sys, 'argv', args), patch('subprocess.run') as run:
            with self.assertRaises(SystemExit): migrate.main()
            run.assert_not_called()

    def test_cloud_host_rejected(self):
        args = ['migrate.py', 'apply', '--host', 'database.example.com', '--database', 'test', '--user', 'owner']
        with patch.object(sys, 'argv', args), patch('subprocess.run') as run:
            with self.assertRaises(SystemExit): migrate.main()
            run.assert_not_called()

    def test_client_uses_explicit_local_target_without_shell(self):
        args = ['migrate.py', 'apply', '--database', 'test', '--user', 'owner']
        env = {'PGHOSTADDR': '203.0.113.1', 'PGSERVICE': 'unwanted', 'PGOPTIONS': '-c search_path=wrong'}
        with patch.object(sys, 'argv', args), patch.dict(os.environ, env), patch('subprocess.run') as run:
            run.return_value.returncode = 0
            self.assertEqual(migrate.main(), 0)
            call = run.call_args
            self.assertIn('127.0.0.1', call.args[0])
            self.assertIn('-X', call.args[0])
            self.assertNotIn('shell', call.kwargs)
            for key in env: self.assertNotIn(key, call.kwargs['env'])


if __name__ == '__main__': unittest.main(verbosity=2)
