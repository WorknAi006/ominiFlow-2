import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("init_env", Path(__file__).parents[1] / "init-env.py")
init_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init_env)


class InitEnvTests(unittest.TestCase):
    def test_generates_matching_database_secret_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'deploy').mkdir()
            (root / '.env.example').write_bytes((Path(__file__).parents[2] / '.env.example').read_bytes())
            with patch.object(init_env, '__file__', str(root / 'deploy' / 'init-env.py')):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    init_env.main()
                original = (root / '.env').read_bytes()
                values = dict(line.split('=', 1) for line in original.decode().splitlines() if '=' in line and not line.startswith('#'))
                self.assertIn(':' + values['POSTGRES_PASSWORD'] + '@postgres:5432/fmfilms', values['DATABASE_URL'])
                self.assertGreaterEqual(len(values['JWT_SECRET']), 32)
                self.assertEqual(values['APP_ENV'], 'production')
                self.assertTrue(values['CHANNEL_CREDENTIAL_KEYS'])
                self.assertNotIn(values['JWT_SECRET'], output.getvalue())
                with contextlib.redirect_stdout(output):
                    init_env.main()
                self.assertEqual((root / '.env').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
