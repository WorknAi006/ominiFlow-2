"""Startup hooks must not crash a fresh install or create a public production admin."""
import unittest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.main import ensure_default_platform_super_admin


class PlatformAdminStartupTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.factory = MagicMock()
        self.factory.return_value.__enter__.return_value = self.session

    def test_production_does_not_create_or_modify_default_account(self):
        for environment in ("production", "prod"):
            with self.subTest(environment=environment), patch.object(settings, "app_env", environment), patch("app.core.database.SessionLocal", self.factory), patch("app.core.security.hash_password") as hasher:
                ensure_default_platform_super_admin()
                self.factory.assert_not_called()
                hasher.assert_not_called()

    def test_fresh_development_account_logs_without_crashing(self):
        self.session.query.return_value.filter.return_value.first.return_value = None
        with patch.object(settings, "app_env", "development"), patch("app.core.database.SessionLocal", self.factory), patch("app.core.security.hash_password", return_value="test-hash"), self.assertLogs("app.main", level="INFO"):
            ensure_default_platform_super_admin()
        self.session.commit.assert_called_once()
        created = self.session.add.call_args.args[0]
        self.assertTrue(created.is_platform_super_admin)
        self.assertEqual(created.password_hash, "test-hash")

    def test_development_database_failure_is_logged_without_crashing(self):
        self.factory.return_value.__enter__.side_effect = RuntimeError("Database unavailable")
        with patch.object(settings, "app_env", "development"), patch("app.core.database.SessionLocal", self.factory), self.assertLogs("app.main", level="WARNING"):
            ensure_default_platform_super_admin()
        self.session.commit.assert_not_called()

    def test_existing_development_admin_is_not_rewritten(self):
        existing = MagicMock(is_platform_super_admin=True, is_active=True)
        self.session.query.return_value.filter.return_value.first.return_value = existing
        with patch.object(settings, "app_env", "development"), patch("app.core.database.SessionLocal", self.factory), patch("app.core.security.hash_password") as hasher:
            ensure_default_platform_super_admin()
        self.session.commit.assert_not_called()
        hasher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
