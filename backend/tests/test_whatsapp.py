"""
Tests for the WhatsApp Cloud API integration: provider verification,
connect flow, webhook verification/signatures, routing and storage.

Meta's Graph API is simulated with httpx.MockTransport; no network calls
are made.
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings
from app.integrations.base import (
    ProviderCredentials,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderNotImplementedError,
)
from app.integrations.meta.graph_client import appsecret_proof, build_graph_client
from app.integrations.meta.webhooks import verify_signature, verify_subscription
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    WhatsAppEvent,
)
from app.services.credential_service import get_credential_service
from tests.base import DatabaseTestCase

APP_ID = "111222333444"
APP_SECRET = f"app-secret-{uuid.uuid4().hex}"
VERIFY_TOKEN = f"verify-{uuid.uuid4().hex}"

WABA = "200000000000001"
PHONE = "100000000000001"
OTHER_PHONE = "100000000000002"

GOOD_TOKEN = f"EAAG-good-{uuid.uuid4().hex}"
EXPIRING_TOKEN = f"EAAG-expiring-{uuid.uuid4().hex}"
WRONG_APP_TOKEN = f"EAAG-wrongapp-{uuid.uuid4().hex}"
NO_SCOPE_TOKEN = f"EAAG-noscope-{uuid.uuid4().hex}"
OTHER_WABA_TOKEN = f"EAAG-otherwaba-{uuid.uuid4().hex}"
NO_ACCESS_TOKEN = f"EAAG-noaccess-{uuid.uuid4().hex}"
BAD_TOKEN = f"EAAG-bad-{uuid.uuid4().hex}"
GOOD_CODE = f"code-{uuid.uuid4().hex}"

ALL_SECRETS = (
    APP_SECRET, GOOD_TOKEN, EXPIRING_TOKEN, WRONG_APP_TOKEN, NO_SCOPE_TOKEN,
    OTHER_WABA_TOKEN, NO_ACCESS_TOKEN, BAD_TOKEN, GOOD_CODE,
)

SCOPES = ["whatsapp_business_management", "whatsapp_business_messaging"]


def _token_data(app_id=APP_ID, scopes=SCOPES, targets=(WABA,), expires_at=0):
    return {
        "is_valid": True,
        "app_id": app_id,
        "expires_at": expires_at,
        "scopes": list(scopes),
        "granular_scopes": [
            {"scope": scope, "target_ids": list(targets)} for scope in scopes
        ],
    }


def _graph_error(status_code, message, code):
    return httpx.Response(
        status_code,
        json={"error": {"message": message, "type": "OAuthException", "code": code}},
    )


class FakeGraph:
    """Simulates the Graph API endpoints used by WhatsAppProvider."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.network_down = False
        self.subscriptions: list[tuple[str, str]] = []
        future = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        self.tokens = {
            GOOD_TOKEN: _token_data(),
            EXPIRING_TOKEN: _token_data(expires_at=future),
            WRONG_APP_TOKEN: _token_data(app_id="999999"),
            NO_SCOPE_TOKEN: _token_data(scopes=["whatsapp_business_messaging"]),
            OTHER_WABA_TOKEN: _token_data(targets=("999999999",)),
            NO_ACCESS_TOKEN: _token_data(targets=()),
        }
        self.token_wabas = {
            GOOD_TOKEN: {WABA},
            EXPIRING_TOKEN: {WABA},
            OTHER_WABA_TOKEN: {WABA},
        }
        self.phones = {
            PHONE: {"id": PHONE, "display_phone_number": "+1 555-0100",
                    "verified_name": "Acme Support", "quality_rating": "GREEN"},
            OTHER_PHONE: {"id": OTHER_PHONE, "display_phone_number": "+1 555-0101",
                          "verified_name": "Acme Sales", "quality_rating": "GREEN"},
        }
        self.wabas = {WABA: {"name": "Acme WABA", "phones": [PHONE]}}
        self.codes = {GOOD_CODE: GOOD_TOKEN}
        # WABA ids whose subscribed_apps GET should report our app missing.
        self.unsubscribed: set[str] = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if self.network_down:
            raise httpx.ConnectError("connection refused", request=request)

        _, _, path = request.url.path.lstrip("/").partition("/")
        params = request.url.params
        auth = request.headers.get("authorization", "")
        token = auth[len("Bearer "):] if auth.startswith("Bearer ") else None

        if path == "oauth/access_token":
            if params.get("client_id") != APP_ID or params.get("client_secret") != APP_SECRET:
                return _graph_error(400, "Error validating client secret.", 1)
            exchanged = self.codes.get(params.get("code"))
            if exchanged is None:
                return _graph_error(400, "Invalid verification code format.", 100)
            return httpx.Response(200, json={"access_token": exchanged, "token_type": "bearer"})

        if path == "debug_token":
            if token != f"{APP_ID}|{APP_SECRET}":
                return _graph_error(400, "Invalid app access token.", 190)
            data = self.tokens.get(params.get("input_token"), {"is_valid": False, "app_id": APP_ID})
            return httpx.Response(200, json={"data": data})

        # User-token endpoints require a valid token and appsecret_proof.
        if token is None or params.get("appsecret_proof") != appsecret_proof(APP_SECRET, token):
            return _graph_error(400, "Invalid appsecret_proof provided.", 100)
        if not self.tokens.get(token, {}).get("is_valid"):
            # Real Meta errors can echo the token; it must be redacted.
            return _graph_error(401, f"Error validating access token: {token}", 190)

        parts = path.split("/")

        if len(parts) == 1 and parts[0] in self.phones:
            return httpx.Response(200, json=self.phones[parts[0]])

        waba_id = parts[0]
        if waba_id not in self.wabas or waba_id not in self.token_wabas.get(token, set()):
            return _graph_error(
                400,
                f"Unsupported get request. Object with ID '{waba_id}' does not "
                f"exist or cannot be loaded with token {token}.",
                100,
            )

        if len(parts) == 1:
            return httpx.Response(200, json={"id": waba_id, "name": self.wabas[waba_id]["name"]})

        if parts[1] == "phone_numbers":
            phones = [self.phones[p] for p in self.wabas[waba_id]["phones"]]
            return httpx.Response(200, json={"data": phones})

        if parts[1] == "subscribed_apps":
            self.subscriptions.append((request.method, waba_id))
            if request.method == "GET":
                apps = [] if waba_id in self.unsubscribed else [
                    {"whatsapp_business_api_data": {"id": APP_ID, "name": "Omniflow"}}
                ]
                return httpx.Response(200, json={"data": apps})
            return httpx.Response(200, json={"success": True})

        return _graph_error(404, "Unknown path.", 100)


class _CaptureHandler(logging.Handler):
    def __init__(self, prefix: str = "") -> None:
        super().__init__(level=logging.DEBUG)
        self.prefix = prefix
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name.startswith(self.prefix):
            return
        text = self.format(record)
        if record.exc_text:
            text += record.exc_text
        self.messages.append(text)


class WhatsAppTestCase(DatabaseTestCase):

    PATCHED_SETTINGS = {
        "meta_app_id": APP_ID,
        "meta_app_secret": APP_SECRET,
        "whatsapp_webhook_verify_token": VERIFY_TOKEN,
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_settings = {
            name: getattr(settings, name)
            for name in (*cls.PATCHED_SETTINGS, "channel_credential_keys")
        }
        for name, value in cls.PATCHED_SETTINGS.items():
            setattr(settings, name, value)
        settings.channel_credential_keys = Fernet.generate_key().decode()

        cls.provider = get_provider(ChannelType.WHATSAPP)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.provider.client_factory = build_graph_client
        for name, value in cls._original_settings.items():
            setattr(settings, name, value)

    def setUp(self) -> None:
        super().setUp()
        self.graph = FakeGraph()
        transport = httpx.MockTransport(self.graph.handler)
        self.provider.client_factory = lambda: build_graph_client(transport=transport)

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("Tenant A")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.manager = cls.make_member(cls.tenant_a, "MANAGER")
        cls.agent = cls.make_member(cls.tenant_a, "AGENT")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")

        cls.tenant_b = cls.make_tenant("Tenant B")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        cls.wa_a = cls.make_channel(cls.tenant_a, ChannelType.WHATSAPP, "WA A")
        cls.ig_a = cls.make_channel(cls.tenant_a, ChannelType.INSTAGRAM, "IG A")
        cls.wa_b = cls.make_channel(cls.tenant_b, ChannelType.WHATSAPP, "WA B")

    @classmethod
    def make_channel(cls, tenant, channel_type, name, **fields):
        channel = ChannelConnection(
            tenant_id=tenant.id,
            channel_type=channel_type,
            name=name,
            status=fields.pop("status", ChannelStatus.PENDING),
            **fields,
        )
        cls.db.add(channel)
        cls.db.flush()
        return channel

    def reload(self, channel):
        self.db.expire_all()
        return self.db.get(ChannelConnection, channel.id)


# =========================
# CONNECT
# =========================

class ConnectTests(WhatsAppTestCase):

    def connect(self, channel, actor=None, tenant=None, **body):
        payload = {"phone_number_id": PHONE, "waba_id": WABA, **body}
        return self.client.post(
            f"/api/v1/channels/{channel.id}/whatsapp/connect",
            headers=self.auth(actor or self.owner, tenant or self.tenant_a),
            json=payload,
        )

    def assert_no_secrets(self, text):
        for secret in ALL_SECRETS:
            self.assertNotIn(secret, text)

    def test_connect_with_access_token(self):
        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["external_account_id"], PHONE)
        self.assertEqual(body["external_business_id"], WABA)
        self.assertTrue(body["has_credentials"])
        self.assertIsNone(body["token_expires_at"])
        self.assertIsNotNone(body["last_connected_at"])
        self.assertIsNone(body["last_error"])
        self.assert_no_secrets(response.text)
        self.assertNotIn("access_token", response.text)

        channel = self.reload(self.wa_a)
        self.assertNotEqual(channel.access_token_encrypted, GOOD_TOKEN)
        self.assertEqual(get_credential_service().decrypt(channel.access_token_encrypted), GOOD_TOKEN)
        self.assertEqual(channel.provider_metadata["display_phone_number"], "+1 555-0100")
        self.assertEqual(channel.provider_metadata["waba_name"], "Acme WABA")

        # Our app was subscribed to the WABA's webhooks.
        self.assertEqual(self.graph.subscriptions, [("POST", WABA)])

    def test_graph_requests_are_authenticated_safely(self):
        self.connect(self.wa_a, access_token=GOOD_TOKEN)

        self.assertTrue(self.graph.requests)
        for request in self.graph.requests:
            with self.subTest(path=request.url.path):
                self.assertNotIn(GOOD_TOKEN, request.url.path)
                if request.url.path.endswith("/debug_token"):
                    continue
                # User token only in the header, with appsecret_proof.
                self.assertEqual(request.headers["authorization"], f"Bearer {GOOD_TOKEN}")
                self.assertNotIn(GOOD_TOKEN, str(request.url))
                self.assertEqual(
                    request.url.params["appsecret_proof"],
                    appsecret_proof(APP_SECRET, GOOD_TOKEN),
                )
                self.assertNotIn(APP_SECRET, str(request.url))

    def test_connect_with_embedded_signup_code(self):
        response = self.connect(self.wa_a, code=GOOD_CODE)
        self.assertEqual(response.status_code, 200, response.text)
        channel = self.reload(self.wa_a)
        self.assertEqual(get_credential_service().decrypt(channel.access_token_encrypted), GOOD_TOKEN)
        self.assert_no_secrets(response.text)

    def test_token_expiry_stored(self):
        response = self.connect(self.wa_a, access_token=EXPIRING_TOKEN)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(response.json()["token_expires_at"])
        self.assertIsNotNone(self.reload(self.wa_a).token_expires_at)

    def test_rbac(self):
        self.assertEqual(self.connect(self.wa_a, self.manager, access_token=GOOD_TOKEN).status_code, 200)
        for actor in (self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                response = self.connect(self.wa_a, actor, access_token=GOOD_TOKEN)
                self.assertEqual(response.status_code, 403)

    def test_verification_failures(self):
        cases = [
            (BAD_TOKEN, "Access token is invalid or expired."),
            (WRONG_APP_TOKEN, "Access token was not issued for this application."),
            (NO_SCOPE_TOKEN, "Access token is missing required permissions: whatsapp_business_management."),
            (OTHER_WABA_TOKEN, "Access token does not grant access to this WhatsApp Business Account."),
        ]
        for token, message in cases:
            with self.subTest(message=message):
                response = self.connect(self.wa_a, access_token=token)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"detail": message})

                channel = self.reload(self.wa_a)
                self.assertEqual(channel.status, "error")
                self.assertEqual(channel.last_error, message)
                self.assertIsNone(channel.access_token_encrypted)
                self.assertIsNone(channel.external_account_id)

        self.assertEqual(self.graph.subscriptions, [])

    def test_phone_not_in_waba_rejected(self):
        self.graph.wabas[WABA]["phones"] = [OTHER_PHONE]
        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Phone number does not belong to this WhatsApp Business Account.",
        )
        self.assertEqual(self.graph.subscriptions, [])

    def test_waba_access_denied_and_message_redacted(self):
        # Token is valid, but Graph refuses the WABA and echoes the token.
        response = self.connect(self.wa_a, access_token=NO_ACCESS_TOKEN)
        self.assertEqual(response.status_code, 400)
        self.assertIn("WhatsApp Business Account could not be verified.", response.text)
        self.assertIn("[redacted]", response.text)
        self.assert_no_secrets(response.text)
        self.assert_no_secrets(self.reload(self.wa_a).last_error)

    def test_invalid_code_rejected(self):
        response = self.connect(self.wa_a, code="code-unknown-123")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("code-unknown-123", response.text)

    def test_meta_unreachable(self):
        self.graph.network_down = True
        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.reload(self.wa_a).status, "error")
        self.assert_no_secrets(response.text)

    def test_invalid_requests_rejected(self):
        invalid = [
            {},
            {"access_token": GOOD_TOKEN, "code": GOOD_CODE},
            {"access_token": GOOD_TOKEN, "phone_number_id": "abc"},
            {"access_token": GOOD_TOKEN, "waba_id": "1 OR 1=1"},
            {"access_token": GOOD_TOKEN, "tenant_id": str(self.tenant_b.id)},
            {"access_token": GOOD_TOKEN, "status": "connected"},
        ]
        for body in invalid:
            with self.subTest(body=list(body)):
                response = self.connect(self.wa_a, **body)
                self.assertEqual(response.status_code, 422)
                self.assert_no_secrets(response.text)

        self.assertEqual(self.graph.requests, [])
        self.assertEqual(self.reload(self.wa_a).status, "pending")

    def test_non_whatsapp_channel_rejected(self):
        response = self.connect(self.ig_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.graph.requests, [])

    def test_cross_tenant_connect_blocked(self):
        response = self.connect(self.wa_b, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 404)

        response = self.connect(self.wa_b, tenant=self.tenant_b, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 403)

        self.assertEqual(self.graph.requests, [])
        self.assertEqual(self.reload(self.wa_b).status, "pending")

    def test_number_connected_elsewhere_conflicts(self):
        wa_b = self.reload(self.wa_b)
        wa_b.status = ChannelStatus.CONNECTED
        wa_b.external_account_id = PHONE
        wa_b.external_business_id = WABA
        self.db.commit()

        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn(str(self.tenant_b.id), response.text)
        self.assertEqual(self.reload(self.wa_b).tenant_id, self.tenant_b.id)

    def test_number_already_used_in_same_tenant_conflicts(self):
        self.make_channel(
            self.tenant_a, ChannelType.WHATSAPP, "Other WA",
            external_account_id=PHONE,
        )
        self.db.commit()
        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 409)

    def test_not_configured(self):
        settings.meta_app_secret = ""
        try:
            response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        finally:
            settings.meta_app_secret = APP_SECRET
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.graph.requests, [])

    def test_failed_reconnect_keeps_connected_channel(self):
        self.assertEqual(self.connect(self.wa_a, access_token=GOOD_TOKEN).status_code, 200)
        before = self.reload(self.wa_a).access_token_encrypted

        response = self.connect(self.wa_a, access_token=BAD_TOKEN)
        self.assertEqual(response.status_code, 400)

        channel = self.reload(self.wa_a)
        self.assertEqual(channel.status, "connected")
        self.assertEqual(channel.access_token_encrypted, before)
        self.assertIsNone(channel.last_error)

    def test_deleted_channel_not_found(self):
        self.client.delete(f"/api/v1/channels/{self.wa_a.id}", headers=self.auth(self.owner, self.tenant_a))
        response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        self.assertEqual(response.status_code, 404)

    def test_missing_encryption_key_fails_closed(self):
        original = settings.channel_credential_keys
        settings.channel_credential_keys = ""
        try:
            response = self.connect(self.wa_a, access_token=GOOD_TOKEN)
        finally:
            settings.channel_credential_keys = original
        self.assertEqual(response.status_code, 503)
        channel = self.reload(self.wa_a)
        self.assertNotEqual(channel.status, "connected")
        self.assertIsNone(channel.access_token_encrypted)

    def test_secrets_not_logged(self):
        handler = _CaptureHandler()
        root = logging.getLogger()
        previous = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            self.connect(self.wa_a, code=GOOD_CODE)
            self.connect(self.wa_a, access_token=NO_ACCESS_TOKEN)
            self.connect(self.wa_a, access_token=BAD_TOKEN)
            self.graph.network_down = True
            self.connect(self.wa_a, access_token=GOOD_TOKEN)
        finally:
            root.removeHandler(handler)
            root.setLevel(previous)

        self.assertTrue(handler.messages)
        self.assert_no_secrets("\n".join(handler.messages))

    def test_provider_metadata_not_exposed(self):
        self.connect(self.wa_a, access_token=GOOD_TOKEN)
        response = self.client.get(
            f"/api/v1/channels/{self.wa_a.id}", headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertNotIn("provider_metadata", response.text)
        self.assertNotIn("_encrypted", response.text)


class ProviderTests(WhatsAppTestCase):

    def test_validate_credentials(self):
        self.assertTrue(self.provider.validate_credentials(ProviderCredentials(GOOD_TOKEN)))
        self.assertFalse(self.provider.validate_credentials(ProviderCredentials(BAD_TOKEN)))
        self.assertFalse(self.provider.validate_credentials(ProviderCredentials(WRONG_APP_TOKEN)))

    def test_connect_interface(self):
        connection = ChannelConnection(external_account_id=PHONE, external_business_id=WABA)
        info = self.provider.connect(connection, ProviderCredentials(GOOD_TOKEN))
        self.assertEqual(info.external_account_id, PHONE)
        self.assertEqual(info.display_name, "Acme Support")
        self.assertEqual(self.graph.subscriptions, [("POST", WABA)])

    def test_get_account_info(self):
        connection = ChannelConnection(external_account_id=PHONE, external_business_id=WABA)
        info = self.provider.get_account_info(connection, ProviderCredentials(GOOD_TOKEN))
        self.assertEqual(info.metadata["display_phone_number"], "+1 555-0100")

    def test_disconnect_unsubscribes(self):
        connection = ChannelConnection(external_account_id=PHONE, external_business_id=WABA)
        self.provider.disconnect(connection, ProviderCredentials(GOOD_TOKEN))
        self.assertEqual(self.graph.subscriptions, [("DELETE", WABA)])

    def test_refresh_token_is_explicit_error(self):
        with self.assertRaises(ProviderError) as ctx:
            self.provider.refresh_token(self.wa_a, ProviderCredentials(GOOD_TOKEN))
        self.assertNotIsInstance(ctx.exception, ProviderNotImplementedError)
        self.assertIn("Reconnect", str(ctx.exception))

    def test_not_configured(self):
        settings.meta_app_id = ""
        try:
            with self.assertRaises(ProviderNotConfiguredError):
                self.provider.validate_credentials(ProviderCredentials(GOOD_TOKEN))
        finally:
            settings.meta_app_id = APP_ID


# =========================
# WEBHOOKS
# =========================

WEBHOOK_URL = "/api/v1/webhooks/whatsapp"

PHONE_A, WABA_A = "300000000000001", "400000000000001"
PHONE_B, WABA_B = "300000000000002", "400000000000002"
CUSTOMER = "15550001111"


def sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def change(phone, *, messages=None, statuses=None, errors=None, contacts=None, **extra):
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550100", "phone_number_id": phone},
        **extra,
    }
    if messages is not None:
        value["messages"] = messages
    if statuses is not None:
        value["statuses"] = statuses
    if errors is not None:
        value["errors"] = errors
    if contacts is not None:
        value["contacts"] = contacts
    return {"field": "messages", "value": value}


def payload(*entries, **extra):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": waba, "changes": changes} for waba, changes in entries],
        **extra,
    }


def text_message(message_id, body="Hello there", sender=CUSTOMER):
    return {
        "from": sender,
        "id": message_id,
        "timestamp": "1767225600",
        "type": "text",
        "text": {"body": body},
    }


class WebhookTests(WhatsAppTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.conn_a = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "Connected A",
            status=ChannelStatus.CONNECTED,
            external_account_id=PHONE_A, external_business_id=WABA_A,
        )
        cls.conn_b = cls.make_channel(
            cls.tenant_b, ChannelType.WHATSAPP, "Connected B",
            status=ChannelStatus.CONNECTED,
            external_account_id=PHONE_B, external_business_id=WABA_B,
        )

    def post(self, body, signature=None, raw=None):
        content = raw if raw is not None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        signature = sign(content) if signature is None else signature
        if signature:
            headers["X-Hub-Signature-256"] = signature
        return self.client.post(WEBHOOK_URL, content=content, headers=headers)

    def events(self, **filters):
        self.db.expire_all()
        return self.db.query(WhatsAppEvent).filter_by(**filters).all()

    # ---------- GET verification ----------

    def verify(self, **params):
        query = {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN,
                 "hub.challenge": "1158201444", **params}
        query = {k: v for k, v in query.items() if v is not None}
        return self.client.get(WEBHOOK_URL, params=query)

    def test_verification_challenge(self):
        response = self.verify()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "1158201444")
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))

    def test_verification_rejections(self):
        cases = {
            "wrong token": {"hub.verify_token": "wrong"},
            "wrong mode": {"hub.mode": "unsubscribe"},
            "missing token": {"hub.verify_token": None},
            "missing challenge": {"hub.challenge": None},
            "script challenge": {"hub.challenge": "<script>alert(1)</script>"},
        }
        for name, params in cases.items():
            with self.subTest(case=name):
                response = self.verify(**params)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("<script>", response.text)

    def test_verification_fails_closed_without_configured_token(self):
        settings.whatsapp_webhook_verify_token = ""
        try:
            self.assertEqual(self.verify(**{"hub.verify_token": ""}).status_code, 403)
            self.assertEqual(self.verify().status_code, 403)
        finally:
            settings.whatsapp_webhook_verify_token = VERIFY_TOKEN

    # ---------- signature ----------

    def test_signature_required(self):
        body = payload((WABA_A, [change(PHONE_A, messages=[text_message("wamid.sig")])]))
        content = json.dumps(body).encode()
        cases = {
            "missing": "",
            "garbage": "sha256=deadbeef",
            "wrong secret": sign(content, "not-the-app-secret"),
            "other body": sign(content + b" "),
            "wrong algorithm": "sha1=" + hmac.new(APP_SECRET.encode(), content, hashlib.sha1).hexdigest(),
        }
        for name, signature in cases.items():
            with self.subTest(case=name):
                response = self.post(body, signature=signature)
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.events(), [])

    def test_signature_helper(self):
        body = b'{"a":1}'
        self.assertTrue(verify_signature(APP_SECRET, body, sign(body)))
        self.assertTrue(verify_signature(APP_SECRET, body, sign(body).upper().replace("SHA256=", "sha256=")))
        self.assertFalse(verify_signature("", body, sign(body)))
        self.assertFalse(verify_signature(APP_SECRET, body, None))
        self.assertFalse(verify_subscription("", "subscribe", "", "123"))

    def test_not_configured(self):
        settings.meta_app_secret = ""
        try:
            response = self.post(payload())
        finally:
            settings.meta_app_secret = APP_SECRET
        self.assertEqual(response.status_code, 503)

    def test_invalid_json_and_size_limit(self):
        response = self.post(None, raw=b"{not json")
        self.assertEqual(response.status_code, 400)

        response = self.post(None, raw=b"x" * 1_000_001)
        self.assertEqual(response.status_code, 413)

    # ---------- routing and storage ----------

    def test_message_stored_for_routed_tenant(self):
        body = payload((WABA_A, [change(
            PHONE_A,
            messages=[text_message("wamid.A1")],
            contacts=[{"wa_id": CUSTOMER, "profile": {"name": "Jane Customer"}}],
        )]))
        response = self.post(body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        [event] = self.events()
        self.assertEqual(event.tenant_id, self.tenant_a.id)
        self.assertEqual(event.channel_id, self.conn_a.id)
        self.assertEqual(event.event_type, "message")
        self.assertEqual(event.wa_message_id, "wamid.A1")
        self.assertEqual(event.wa_id, CUSTOMER)
        self.assertEqual(event.processing_status, "received")
        self.assertEqual(event.occurred_at, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(event.payload["message"]["text"]["body"], "Hello there")
        self.assertEqual(event.payload["contact"]["profile"]["name"], "Jane Customer")

    def test_duplicate_delivery_stored_once(self):
        body = payload((WABA_A, [change(PHONE_A, messages=[text_message("wamid.dup")])]))
        for _ in range(3):
            self.assertEqual(self.post(body).status_code, 200)
        self.assertEqual(len(self.events(wa_message_id="wamid.dup")), 1)

    def test_statuses_and_errors_stored(self):
        statuses = [
            {"id": "wamid.out1", "status": "sent", "timestamp": "1767225600", "recipient_id": CUSTOMER},
            {"id": "wamid.out1", "status": "delivered", "timestamp": "1767225601", "recipient_id": CUSTOMER},
        ]
        errors = [{"code": 131047, "title": "Re-engagement message"}]
        body = payload((WABA_A, [change(PHONE_A, statuses=statuses, errors=errors)]))
        self.post(body)
        self.post(body)

        self.assertEqual(len(self.events(event_type="status")), 2)
        self.assertEqual(len(self.events(event_type="error")), 1)

    def test_unroutable_changes_dropped(self):
        cases = {
            "unknown phone": payload(("999", [change("999", messages=[text_message("wamid.x1")])])),
            "waba mismatch": payload((WABA_B, [change(PHONE_A, messages=[text_message("wamid.x2")])])),
            "other object": {"object": "page", "entry": []},
            "other field": payload((WABA_A, [{"field": "account_update", "value": {}}])),
            "malformed": {"object": "whatsapp_business_account", "entry": "nope"},
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.post(body).status_code, 200)
        self.assertEqual(self.events(), [])

    def test_disconnected_or_inactive_channel_not_routed(self):
        self.client.post(
            f"/api/v1/channels/{self.conn_a.id}/disconnect",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.post(payload((WABA_A, [change(PHONE_A, messages=[text_message("wamid.d1")])])))

        conn_b = self.reload(self.conn_b)
        conn_b.is_active = False
        self.db.commit()
        self.post(payload((WABA_B, [change(PHONE_B, messages=[text_message("wamid.d2")])])))

        self.assertEqual(self.events(), [])

    def test_payload_tenant_fields_are_ignored(self):
        # Attacker-controlled fields cannot redirect the event.
        body = payload(
            (WABA_A, [change(
                PHONE_A,
                messages=[text_message("wamid.t1")],
                tenant_id=str(self.tenant_b.id),
                channel_id=str(self.conn_b.id),
            )]),
            tenant_id=str(self.tenant_b.id),
        )
        self.post(body)
        [event] = self.events()
        self.assertEqual(event.tenant_id, self.tenant_a.id)
        self.assertEqual(event.channel_id, self.conn_a.id)
        self.assertEqual(self.events(tenant_id=self.tenant_b.id), [])

    def test_multi_tenant_payload_routed_independently(self):
        body = payload(
            (WABA_A, [change(PHONE_A, messages=[text_message("wamid.m1")])]),
            (WABA_B, [change(PHONE_B, messages=[text_message("wamid.m2")])]),
        )
        self.post(body)
        self.assertEqual([e.wa_message_id for e in self.events(tenant_id=self.tenant_a.id)], ["wamid.m1"])
        self.assertEqual([e.wa_message_id for e in self.events(tenant_id=self.tenant_b.id)], ["wamid.m2"])

    def test_events_not_exposed_through_channel_api(self):
        self.post(payload((WABA_A, [change(PHONE_A, messages=[text_message("wamid.e1")])])))
        response = self.client.get(
            "/api/v1/channels", headers=self.auth(self.owner_b, self.tenant_b)
        )
        self.assertNotIn("wamid.e1", response.text)

    def test_customer_content_not_logged(self):
        # Application loggers only: SQLAlchemy's own DEBUG output logs SQL
        # parameters (the stored payload) and is never enabled in prod.
        handler = _CaptureHandler(prefix="app.")
        root = logging.getLogger()
        previous = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            secret_text = f"private-message-{uuid.uuid4().hex}"
            self.post(payload((WABA_A, [change(
                PHONE_A, messages=[text_message("wamid.log", body=secret_text)],
            )])))
        finally:
            root.removeHandler(handler)
            root.setLevel(previous)

        logged = "\n".join(handler.messages)
        self.assertIn("WhatsApp webhook processed", logged)
        self.assertNotIn(secret_text, logged)
        self.assertNotIn(CUSTOMER, logged)
        self.assertNotIn(APP_SECRET, logged)


# =========================
# TEST CONNECTION (read-only health check)
# =========================

TEST_URL = "/api/v1/channels/{id}/whatsapp/test"


class TestConnectionTests(WhatsAppTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.connected = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "Connected",
            status=ChannelStatus.CONNECTED,
            external_account_id=PHONE, external_business_id=WABA,
            access_token_encrypted=get_credential_service().encrypt(GOOD_TOKEN),
        )
        cls.pending = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "Pending",
            status=ChannelStatus.PENDING,
        )
        cls.bad_creds = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "Bad Creds",
            status=ChannelStatus.CONNECTED,
            external_account_id=OTHER_PHONE, external_business_id=WABA,
            access_token_encrypted=get_credential_service().encrypt(BAD_TOKEN),
        )
        cls.connected_b = cls.make_channel(
            cls.tenant_b, ChannelType.WHATSAPP, "Connected B",
            status=ChannelStatus.CONNECTED,
            external_account_id="100000000000009", external_business_id=WABA,
            access_token_encrypted=get_credential_service().encrypt(GOOD_TOKEN),
        )

    def check(self, channel, actor=None, tenant=None):
        return self.client.post(
            TEST_URL.format(id=channel.id),
            headers=self.auth(actor or self.owner, tenant or self.tenant_a),
        )

    def assert_no_secrets(self, text):
        for secret in ALL_SECRETS:
            self.assertNotIn(secret, text)

    def test_healthy_connection(self):
        response = self.check(self.connected)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["healthy"])
        self.assertIn("healthy", body["detail"])
        self.assertTrue(body["webhook_subscribed"])
        self.assertEqual(body["display_phone_number"], "+1 555-0100")
        self.assertEqual(body["verified_name"], "Acme Support")
        self.assertIsNone(body["last_event_at"])
        self.assert_no_secrets(response.text)

        # The check is read-only: status and credentials are untouched.
        channel = self.reload(self.connected)
        self.assertEqual(channel.status, ChannelStatus.CONNECTED)
        self.assertIsNotNone(channel.access_token_encrypted)

    def test_webhook_not_subscribed_is_reported(self):
        self.graph.unsubscribed.add(WABA)
        body = self.check(self.connected).json()
        self.assertTrue(body["healthy"])
        self.assertFalse(body["webhook_subscribed"])

    def test_invalid_token_is_unhealthy_not_error(self):
        response = self.check(self.bad_creds)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["healthy"])
        self.assertTrue(body["detail"])
        self.assert_no_secrets(response.text)

    def test_not_connected_channel_skips_meta(self):
        response = self.check(self.pending)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["healthy"])
        self.assertIn("not connected", body["detail"])
        self.assertIsNone(body["webhook_subscribed"])
        self.assertEqual(self.graph.requests, [])

    def test_non_whatsapp_channel_rejected(self):
        response = self.check(self.ig_a)
        self.assertEqual(response.status_code, 422)

    def test_meta_unavailable_returns_502(self):
        self.graph.network_down = True
        response = self.check(self.connected)
        self.assertEqual(response.status_code, 502)
        self.assert_no_secrets(response.text)

    def test_requires_channel_update_permission(self):
        for actor in (self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.check(self.connected, actor=actor).status_code, 403)
        for actor in (self.owner, self.manager):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.check(self.connected, actor=actor).status_code, 200)

    def test_cross_tenant_blocked(self):
        response = self.check(self.connected_b, actor=self.owner, tenant=self.tenant_a)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.graph.requests, [])

    def test_unknown_channel_404(self):
        self.assertEqual(
            self.client.post(
                TEST_URL.format(id=uuid.uuid4()),
                headers=self.auth(self.owner, self.tenant_a),
            ).status_code,
            404,
        )
