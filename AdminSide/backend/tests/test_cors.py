import unittest

from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


class FrontendOriginsTests(unittest.TestCase):
    def test_comma_separated_origins_are_trimmed(self):
        config = Settings.model_construct(
            frontend_url="http://legacy.example",
            frontend_origins=" https://one.example, http://localhost:3000/,,",
        )

        self.assertEqual(
            config.allowed_frontend_origins,
            ["https://one.example", "http://localhost:3000"],
        )

    def test_existing_frontend_url_remains_the_fallback(self):
        config = Settings.model_construct(
            frontend_url="https://configured.example/",
            frontend_origins="",
        )

        self.assertEqual(
            config.allowed_frontend_origins,
            ["https://configured.example"],
        )


class CORSMiddlewareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.allowed_origin = settings.allowed_frontend_origins[0]

    def test_configured_origin_can_make_preflighted_api_request(self):
        response = self.client.options(
            "/health",
            headers={
                "Origin": self.allowed_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            self.allowed_origin,
        )

    def test_unconfigured_origin_is_not_granted_cors_access(self):
        response = self.client.get(
            "/health",
            headers={"Origin": "https://untrusted.example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)
