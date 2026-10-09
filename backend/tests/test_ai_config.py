import json
import uuid
from unittest.mock import patch

from sqlalchemy import select

from app.models.tenant_ai_config import TenantAiConfig
from app.services.credential_service import get_credential_service
from tests.base import DatabaseTestCase

class TestAiConfig(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a = self.make_tenant("Tenant A")
        self.tenant_b = self.make_tenant("Tenant B")
        self.admin_a = self.make_member(self.tenant_a, "ADMIN")
        self.admin_b = self.make_member(self.tenant_b, "ADMIN")

    def test_01_get_default_config_when_none_exists(self):
        """When a tenant has no configuration, they should receive the default platform configuration."""
        response = self.client.get(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider"], "platform")
        self.assertEqual(data["model"], "gpt-4o")
        self.assertFalse(data["has_api_key"])

    def test_02_update_config_and_encrypt_key(self):
        """Updates AI configuration and ensures the API key is encrypted before storage."""
        response = self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4-turbo",
                "api_key": "sk-super-secret-key"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider"], "openai")
        self.assertEqual(data["model"], "gpt-4-turbo")
        self.assertTrue(data["has_api_key"])
        self.assertNotIn("api_key", data)
        self.assertNotIn("sk-super-secret-key", json.dumps(data))

        # Verify database encryption
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config = self.db.scalars(stmt).first()
        
        self.assertIsNotNone(config)
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model, "gpt-4-turbo")
        
        # Key should be encrypted
        self.assertIsNotNone(config.api_key_encrypted)
        self.assertNotEqual(config.api_key_encrypted, "sk-super-secret-key")
        self.assertNotIn("sk-super-secret-key", config.api_key_encrypted)
        
        # Decrypt matches original
        service = get_credential_service()
        self.assertEqual(service.decrypt(config.api_key_encrypted), "sk-super-secret-key")

    def test_03_tenant_isolation(self):
        """Configuration changes for one tenant should not affect another."""
        # Tenant A sets config
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "sk-tenant-a"
            }
        )
        
        # Tenant B token shouldn't see A's config
        response_b = self.client.get(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_b, self.tenant_b)
        )
        self.assertEqual(response_b.status_code, 200)
        data_b = response_b.json()
        self.assertEqual(data_b["provider"], "platform")
        self.assertFalse(data_b["has_api_key"])

    def test_04_clear_api_key(self):
        """Passing an empty string for the API key should clear it."""
        # Set
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-to-clear"
            }
        )
        
        # Clear
        response = self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": ""
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_api_key"])
        
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config = self.db.scalars(stmt).first()
        self.assertIsNone(config.api_key_encrypted)

    def test_05_update_without_modifying_key(self):
        """Passing null or omitting api_key should not modify the existing encrypted key."""
        # Set
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-to-keep"
            }
        )
        
        # Read encrypted value directly to compare later
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config_before = self.db.scalars(stmt).first()
        encrypted_before = config_before.api_key_encrypted
            
        # Update model only
        response = self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4-turbo"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["has_api_key"])
        
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config_after = self.db.scalars(stmt).first()
        self.assertEqual(config_after.api_key_encrypted, encrypted_before)

    @patch("httpx.Client.get")
    def test_06_validate_api_key_success(self, mock_get):
        """Validation should successfully verify an API key and update state."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-valid-key"
            }
        )
        
        import unittest.mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        response = self.client.post(
            "/api/v1/ai-config/validate",
            headers=self.auth(self.admin_a, self.tenant_a)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "valid")
        self.assertEqual(data["message"], "Configuration is valid.")
        
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config = self.db.scalars(stmt).first()
        self.assertTrue(config.is_verified)

    @patch("httpx.Client.get")
    def test_07_validate_api_key_failure(self, mock_get):
        """Validation should safely handle failed validation."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-invalid-key"
            }
        )
        
        import unittest.mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        response = self.client.post(
            "/api/v1/ai-config/validate",
            headers=self.auth(self.admin_a, self.tenant_a)
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "invalid")
        self.assertEqual(data["message"], "Invalid credentials.")
        
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config = self.db.scalars(stmt).first()
        self.assertFalse(config.is_verified)

    @patch("httpx.Client.get")
    def test_08_validate_api_key_rate_limit(self, mock_get):
        """Validation should handle 429 rate limits without marking invalid."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-rate-limited"
            }
        )
        import unittest.mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        response = self.client.post("/api/v1/ai-config/validate", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "rate_limited")
        self.assertIn("rate limit", data["message"])
        
        stmt = select(TenantAiConfig).where(TenantAiConfig.tenant_id == self.tenant_a.id)
        config = self.db.scalars(stmt).first()
        self.assertFalse(config.is_verified)

    @patch("httpx.Client.get")
    def test_09_validate_api_key_quota(self, mock_get):
        """Validation should identify quota issues."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-quota"
            }
        )
        import unittest.mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"code": "insufficient_quota"}}
        mock_get.return_value = mock_response
        
        response = self.client.post("/api/v1/ai-config/validate", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "rate_limited")
        self.assertIn("quota", data["message"])

    @patch("httpx.Client.get")
    def test_10_validate_api_key_temporary_failure(self, mock_get):
        """Validation should safely handle 5xx server errors."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-500"
            }
        )
        import unittest.mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        response = self.client.post("/api/v1/ai-config/validate", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "temporary_failure")

    @patch("httpx.Client.get")
    def test_11_validate_api_key_timeout(self, mock_get):
        """Validation should gracefully handle network timeouts."""
        self.client.put(
            "/api/v1/ai-config",
            headers=self.auth(self.admin_a, self.tenant_a),
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-timeout"
            }
        )
        import httpx
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        
        response = self.client.post("/api/v1/ai-config/validate", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "temporary_failure")
        self.assertIn("timed out", data["message"])
