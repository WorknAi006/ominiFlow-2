"""
Tests for Channel Connections: RBAC, tenant isolation, CRUD lifecycle,
credential encryption, provider abstraction and webhook routing lookup.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.integrations.base import (
    ProviderCredentials,
    ProviderNotImplementedError,
)
from app.integrations.registry import get_provider
from app.models import ChannelConnection, ChannelStatus, ChannelType
from app.services import channel_service
from app.services.credential_service import (
    ChannelCredentialService,
    get_credential_service,
)
from tests.base import DatabaseTestCase, bearer

CHANNELS_URL = "/api/v1/channels"

RESPONSE_FIELDS = {
    "id", "name", "channel_type", "status", "external_account_id",
    "external_business_id", "has_credentials", "token_expires_at",
    "is_active", "last_connected_at", "last_error", "created_at",
    "updated_at",
}

SECRET_FIELD_NAMES = (
    "access_token", "refresh_token", "_encrypted", "provider_metadata",
)

FORBIDDEN = {"detail": "You do not have permission to perform this action."}


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


class ChannelTestCase(DatabaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_keys = settings.channel_credential_keys
        cls.test_key = Fernet.generate_key().decode()
        settings.channel_credential_keys = cls.test_key
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        settings.channel_credential_keys = cls._original_keys

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("Tenant A")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.admin = cls.make_member(cls.tenant_a, "ADMIN")
        cls.manager = cls.make_member(cls.tenant_a, "MANAGER")
        cls.agent = cls.make_member(cls.tenant_a, "AGENT")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")
        cls.developer = cls.make_member(cls.tenant_a, "DEVELOPER")

        cls.tenant_b = cls.make_tenant("Tenant B")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        cls.wa_a = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "Support WhatsApp",
            ChannelStatus.CONNECTED, "1001",
        )
        cls.ig_a = cls.make_channel(
            cls.tenant_a, ChannelType.INSTAGRAM, "Brand Instagram",
            ChannelStatus.PENDING, "ig_2002",
        )
        cls.fb_a = cls.make_channel(
            cls.tenant_a, ChannelType.FACEBOOK, "Main Page",
            ChannelStatus.ERROR, None,
        )
        cls.wa_b = cls.make_channel(
            cls.tenant_b, ChannelType.WHATSAPP, "Tenant B WhatsApp",
            ChannelStatus.CONNECTED, "9009",
        )

    @classmethod
    def make_channel(cls, tenant, channel_type, name, status, external_id):
        channel = ChannelConnection(
            tenant_id=tenant.id,
            channel_type=channel_type,
            name=name,
            status=status,
            external_account_id=external_id,
            access_token_encrypted=get_credential_service().encrypt(
                f"fixture-token-{uuid.uuid4().hex}"
            ),
        )
        cls.db.add(channel)
        cls.db.flush()
        return channel

    # ---------- helpers ----------

    def url(self, channel, suffix=""):
        channel_id = channel if isinstance(channel, (str, uuid.UUID)) else channel.id
        return f"{CHANNELS_URL}/{channel_id}{suffix}"

    def create(self, actor, body, tenant=None):
        return self.client.post(
            CHANNELS_URL,
            headers=self.auth(actor, tenant or self.tenant_a),
            json=body,
        )

    def list_names(self, actor, query=""):
        response = self.client.get(
            f"{CHANNELS_URL}{query}", headers=self.auth(actor, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {item["name"] for item in response.json()["items"]}

    def raw_row(self, channel_id):
        return self.connection.execute(
            text(
                "SELECT access_token_encrypted, refresh_token_encrypted, "
                "token_expires_at, status, is_deleted, is_active "
                "FROM channel_connections WHERE id = :id"
            ),
            {"id": channel_id},
        ).mappings().one()

    def assert_no_secrets(self, response):
        for name in SECRET_FIELD_NAMES:
            self.assertNotIn(name, response.text)


class AuthTests(ChannelTestCase):

    def test_01_missing_jwt(self):
        self.assertEqual(self.client.get(CHANNELS_URL).status_code, 401)

    def test_02_invalid_jwt(self):
        response = self.client.get(CHANNELS_URL, headers=bearer("bad.jwt.token"))
        self.assertEqual(response.status_code, 401)

    def test_03_missing_permission(self):
        response = self.client.delete(
            self.url(self.ig_a), headers=self.auth(self.manager, self.tenant_a)
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), FORBIDDEN)


class ListTests(ChannelTestCase):

    def test_04_to_06_read_roles_can_list(self):
        expected = {"Support WhatsApp", "Brand Instagram", "Main Page"}
        for actor in (self.owner, self.admin, self.manager,
                      self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.list_names(actor), expected)

    def test_response_shape(self):
        response = self.client.get(
            CHANNELS_URL, headers=self.auth(self.owner, self.tenant_a)
        )
        body = response.json()
        self.assertEqual(body["total"], 3)
        for item in body["items"]:
            self.assertEqual(set(item), RESPONSE_FIELDS)
            self.assertTrue(item["has_credentials"])

    def test_07_pagination(self):
        headers = self.auth(self.owner, self.tenant_a)
        page_1 = self.client.get(f"{CHANNELS_URL}?page=1&page_size=2", headers=headers).json()
        page_2 = self.client.get(f"{CHANNELS_URL}?page=2&page_size=2", headers=headers).json()

        self.assertEqual((page_1["total"], len(page_1["items"])), (3, 2))
        self.assertEqual((page_2["total"], len(page_2["items"])), (3, 1))
        ids = [item["id"] for item in page_1["items"] + page_2["items"]]
        self.assertEqual(len(set(ids)), 3)

        for query in ("?page=0", "?page_size=0", "?page_size=101"):
            with self.subTest(query=query):
                response = self.client.get(f"{CHANNELS_URL}{query}", headers=headers)
                self.assertEqual(response.status_code, 422)

    def test_08_channel_type_filter(self):
        self.assertEqual(
            self.list_names(self.owner, "?channel_type=whatsapp"),
            {"Support WhatsApp"},
        )
        response = self.client.get(
            f"{CHANNELS_URL}?channel_type=telegram",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 422)

    def test_09_status_filter(self):
        self.assertEqual(
            self.list_names(self.owner, "?status=connected"), {"Support WhatsApp"}
        )
        self.assertEqual(self.list_names(self.owner, "?status=error"), {"Main Page"})
        self.assertEqual(
            self.list_names(self.owner, "?status=pending&channel_type=whatsapp"),
            set(),
        )
        response = self.client.get(
            f"{CHANNELS_URL}?status=bogus",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 422)

    def test_search(self):
        self.assertEqual(self.list_names(self.owner, "?search=BRAND"), {"Brand Instagram"})
        self.assertEqual(self.list_names(self.owner, "?search=1001"), {"Support WhatsApp"})
        self.assertEqual(self.list_names(self.owner, "?search=%25"), set())
        self.assertEqual(self.list_names(self.owner, "?search=Tenant B"), set())

    def test_get_channel(self):
        response = self.client.get(
            self.url(self.wa_a), headers=self.auth(self.viewer, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), RESPONSE_FIELDS)
        self.assertEqual(body["channel_type"], "whatsapp")
        self.assertEqual(body["status"], "connected")

        response = self.client.get(
            self.url(uuid.uuid4()), headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            self.url("not-a-uuid"), headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.status_code, 422)


class CreateTests(ChannelTestCase):

    def test_10_to_12_create_roles(self):
        for index, actor in enumerate((self.owner, self.admin, self.manager)):
            with self.subTest(actor=actor.email):
                response = self.create(actor, {
                    "channel_type": "whatsapp",
                    "name": f"  New Channel {index} ",
                    "external_account_id": f"55500{index}",
                    "external_business_id": "waba_1",
                })
                self.assertEqual(response.status_code, 201, response.text)
                body = response.json()
                self.assertEqual(body["status"], "pending")
                self.assertEqual(body["name"], f"New Channel {index}")
                self.assertFalse(body["has_credentials"])
                self.assertTrue(body["is_active"])

                stored = self.db.get(ChannelConnection, uuid.UUID(body["id"]))
                self.assertEqual(stored.tenant_id, self.tenant_a.id)
                self.assertEqual(stored.created_by, actor.id)

    def test_13_14_agent_viewer_developer_cannot_create(self):
        for actor in (self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.create(actor, {"channel_type": "facebook", "name": "Nope"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), FORBIDDEN)

    def test_15_invalid_input_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        invalid = [
            {"channel_type": "telegram", "name": "Bad Type"},
            {"channel_type": "WhatsApp ", "name": "Bad Type"},
            {"name": "No Type"},
            {"channel_type": "whatsapp"},
            {"channel_type": "whatsapp", "name": "x"},
            {"channel_type": "whatsapp", "name": "x" * 151},
            {"channel_type": "whatsapp", "name": "Bad Id", "external_account_id": "has space"},
            {"channel_type": "whatsapp", "name": "Bad Id", "external_account_id": "a'; DROP"},
            {"channel_type": "whatsapp", "name": "Status", "status": "connected"},
            {"channel_type": "whatsapp", "name": "Tenant", "tenant_id": str(self.tenant_b.id)},
            {"channel_type": "whatsapp", "name": "Meta", "provider_metadata": {}},
            {"channel_type": "whatsapp", "name": "Refresh", "refresh_token": "r-only"},
            {"channel_type": "whatsapp", "name": "Expiry", "token_expires_at": future},
            {"channel_type": "whatsapp", "name": "Past", "access_token": "t", "token_expires_at": past},
            {"channel_type": "whatsapp", "name": "Naive", "access_token": "t",
             "token_expires_at": "2099-01-01T00:00:00"},
        ]
        for body in invalid:
            with self.subTest(body=body):
                self.assertEqual(self.create(self.owner, body).status_code, 422)

    def test_validation_error_does_not_echo_access_token(self):
        secret = f"echo-check-{uuid.uuid4().hex}"
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        response = self.create(self.owner, {
            "channel_type": "whatsapp", "name": "Echo",
            "access_token": secret, "token_expires_at": past,
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)

    def test_duplicate_external_account_in_tenant(self):
        response = self.create(self.owner, {
            "channel_type": "whatsapp", "name": "Dup", "external_account_id": "1001",
        })
        self.assertEqual(response.status_code, 409)

        # Same id on a different channel type is fine.
        response = self.create(self.owner, {
            "channel_type": "facebook", "name": "Other Type", "external_account_id": "1001",
        })
        self.assertEqual(response.status_code, 201)

    def test_pending_claim_does_not_block_other_tenant(self):
        # Tenant A cannot squat tenant B's connected account; it can only
        # create an unverified pending record, which is never routable.
        response = self.create(self.owner, {
            "channel_type": "whatsapp", "name": "Squat", "external_account_id": "9009",
        })
        self.assertEqual(response.status_code, 201)

        found = channel_service.find_connected_channel(
            self.db, ChannelType.WHATSAPP, "9009"
        )
        self.assertEqual(found.tenant_id, self.tenant_b.id)

        # The database refuses two connected owners of one account.
        squat = self.db.get(ChannelConnection, uuid.UUID(response.json()["id"]))
        squat.status = ChannelStatus.CONNECTED
        with self.assertRaises(IntegrityError):
            self.db.commit()


class UpdateTests(ChannelTestCase):

    def patch(self, actor, channel, body, tenant=None):
        return self.client.patch(
            self.url(channel),
            headers=self.auth(actor, tenant or self.tenant_a),
            json=body,
        )

    def test_16_to_18_update_roles(self):
        for actor in (self.owner, self.admin, self.manager):
            with self.subTest(actor=actor.email):
                name = f"Renamed by {actor.first_name} {uuid.uuid4().hex[:4]}"
                response = self.patch(actor, self.ig_a, {"name": name, "is_active": False})
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["name"], name)
                self.assertFalse(body["is_active"])
                self.assertEqual(body["status"], "pending")

    def test_19_20_agent_viewer_cannot_update(self):
        for actor in (self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.patch(actor, self.ig_a, {"name": "Nope Name"})
                self.assertEqual(response.status_code, 403)

    def test_only_safe_fields_updatable(self):
        protected = [
            {"status": "connected"},
            {"channel_type": "facebook"},
            {"access_token": "new-token"},
            {"refresh_token": "new-token"},
            {"access_token_encrypted": "x"},
            {"external_account_id": "777"},
            {"tenant_id": str(self.tenant_b.id)},
            {"last_error": "x"},
            {"is_deleted": True},
            {"created_by": str(self.owner.id)},
            {},
            {"name": None},
            {"is_active": None},
            {"name": "x"},
        ]
        for body in protected:
            with self.subTest(body=body):
                self.assertEqual(self.patch(self.owner, self.wa_a, body).status_code, 422)

        row = self.raw_row(self.wa_a.id)
        self.assertEqual(row["status"], "connected")
        self.assertIsNotNone(row["access_token_encrypted"])


class DisconnectDeleteTests(ChannelTestCase):

    def test_21_authorized_can_disconnect(self):
        for actor, channel in ((self.manager, self.wa_a), (self.admin, self.ig_a),
                               (self.owner, self.fb_a)):
            with self.subTest(actor=actor.email):
                response = self.client.post(
                    self.url(channel, "/disconnect"),
                    headers=self.auth(actor, self.tenant_a),
                )
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["status"], "disconnected")
                self.assertFalse(body["has_credentials"])

                row = self.raw_row(channel.id)
                self.assertIsNone(row["access_token_encrypted"])
                self.assertIsNone(row["refresh_token_encrypted"])
                self.assertFalse(row["is_deleted"])

        # Disconnected channels are no longer routable for webhooks.
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.WHATSAPP, "1001"
        ))

        # Disconnect is idempotent.
        response = self.client.post(
            self.url(self.wa_a, "/disconnect"), headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)

    def test_22_unauthorized_cannot_disconnect(self):
        for actor in (self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.client.post(
                    self.url(self.wa_a, "/disconnect"),
                    headers=self.auth(actor, self.tenant_a),
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.raw_row(self.wa_a.id)["status"], "connected")

    def test_23_authorized_can_delete(self):
        for actor, channel in ((self.owner, self.wa_a), (self.admin, self.ig_a)):
            with self.subTest(actor=actor.email):
                headers = self.auth(actor, self.tenant_a)
                response = self.client.delete(self.url(channel), headers=headers)
                self.assertEqual(response.status_code, 204)

                # Soft delete: row kept, hidden, credentials wiped.
                row = self.raw_row(channel.id)
                self.assertTrue(row["is_deleted"])
                self.assertFalse(row["is_active"])
                self.assertIsNone(row["access_token_encrypted"])

                self.assertEqual(self.client.get(self.url(channel), headers=headers).status_code, 404)
                self.assertEqual(self.client.delete(self.url(channel), headers=headers).status_code, 404)
                self.assertEqual(
                    self.client.post(self.url(channel, "/disconnect"), headers=headers).status_code,
                    404,
                )

        self.assertEqual(self.list_names(self.owner), {"Main Page"})

        # A deleted channel's external account can be connected again.
        response = self.create(self.owner, {
            "channel_type": "whatsapp", "name": "Recreated", "external_account_id": "1001",
        })
        self.assertEqual(response.status_code, 201)

    def test_24_unauthorized_cannot_delete(self):
        for actor in (self.manager, self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.client.delete(
                    self.url(self.ig_a), headers=self.auth(actor, self.tenant_a)
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(self.raw_row(self.ig_a.id)["is_deleted"])

    def test_25_cross_tenant_delete_blocked(self):
        response = self.client.delete(
            self.url(self.wa_b), headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.raw_row(self.wa_b.id)["is_deleted"])


class TenantIsolationTests(ChannelTestCase):

    def test_26_cannot_list_other_tenant(self):
        names = self.list_names(self.owner)
        self.assertNotIn("Tenant B WhatsApp", names)
        names = self.list_names(self.owner, f"?tenant_id={self.tenant_b.id}")
        self.assertNotIn("Tenant B WhatsApp", names)

        response = self.client.get(
            CHANNELS_URL, headers=self.auth(self.owner_b, self.tenant_b)
        )
        self.assertEqual(
            {item["name"] for item in response.json()["items"]},
            {"Tenant B WhatsApp"},
        )

    def test_27_to_30_cannot_touch_other_tenant_channel(self):
        headers = self.auth(self.owner, self.tenant_a)
        target = self.url(self.wa_b)
        not_found = {"detail": "Channel not found."}

        calls = {
            "read": self.client.get(target, headers=headers),
            "read_with_query": self.client.get(
                f"{target}?tenant_id={self.tenant_b.id}", headers=headers
            ),
            "update": self.client.patch(target, headers=headers, json={"name": "Hacked"}),
            "disconnect": self.client.post(f"{target}/disconnect", headers=headers),
            "delete": self.client.delete(target, headers=headers),
        }
        for action, response in calls.items():
            with self.subTest(action=action):
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), not_found)

        row = self.raw_row(self.wa_b.id)
        self.assertEqual(row["status"], "connected")
        self.assertFalse(row["is_deleted"])
        self.assertIsNotNone(row["access_token_encrypted"])
        self.db.expire_all()
        self.assertEqual(self.db.get(ChannelConnection, self.wa_b.id).name, "Tenant B WhatsApp")

    def test_token_for_foreign_tenant_rejected(self):
        response = self.client.get(
            self.url(self.wa_b), headers=self.auth(self.owner, self.tenant_b)
        )
        self.assertEqual(response.status_code, 403)

    def test_tenant_id_in_body_rejected(self):
        response = self.create(self.owner, {
            "channel_type": "whatsapp", "name": "Body Scope",
            "tenant_id": str(self.tenant_b.id),
        })
        self.assertEqual(response.status_code, 422)


class CredentialSecurityTests(ChannelTestCase):

    def create_with_credentials(self, access, refresh):
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        response = self.create(self.owner, {
            "channel_type": "instagram",
            "name": "With Credentials",
            "access_token": access,
            "refresh_token": refresh,
            "token_expires_at": expires,
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response

    def test_31_32_tokens_never_returned(self):
        access = f"access-{uuid.uuid4().hex}"
        refresh = f"refresh-{uuid.uuid4().hex}"
        created = self.create_with_credentials(access, refresh)
        channel_id = created.json()["id"]
        self.assertTrue(created.json()["has_credentials"])
        self.assertIsNotNone(created.json()["token_expires_at"])

        headers = self.auth(self.owner, self.tenant_a)
        responses = [
            created,
            self.client.get(CHANNELS_URL, headers=headers),
            self.client.get(self.url(channel_id), headers=headers),
            self.client.patch(self.url(channel_id), headers=headers, json={"name": "Renamed"}),
        ]
        encrypted = self.raw_row(channel_id)["access_token_encrypted"]
        for response in responses:
            with self.subTest(url=str(response.url), method=response.request.method):
                self.assertNotIn(access, response.text)
                self.assertNotIn(refresh, response.text)
                self.assertNotIn(encrypted, response.text)
                self.assert_no_secrets(response)

        openapi = self.client.get("/openapi.json").json()
        response_schema = openapi["components"]["schemas"]["ChannelConnectionResponse"]
        for name in response_schema["properties"]:
            self.assertNotIn("token_encrypted", name)
            self.assertNotIn(name, ("access_token", "refresh_token"))

    def test_33_credentials_encrypted_at_rest(self):
        access = f"access-{uuid.uuid4().hex}"
        refresh = f"refresh-{uuid.uuid4().hex}"
        channel_id = self.create_with_credentials(access, refresh).json()["id"]

        row = self.raw_row(channel_id)
        self.assertNotEqual(row["access_token_encrypted"], access)
        self.assertNotIn(access, row["access_token_encrypted"])
        self.assertTrue(row["access_token_encrypted"].startswith("gAAAAA"))

        service = get_credential_service()
        self.assertEqual(service.decrypt(row["access_token_encrypted"]), access)
        self.assertEqual(service.decrypt(row["refresh_token_encrypted"]), refresh)

        # Plaintext does not appear anywhere in the row.
        dump = self.connection.execute(
            text("SELECT row_to_json(c)::text FROM channel_connections c WHERE id = :id"),
            {"id": channel_id},
        ).scalar()
        self.assertNotIn(access, dump)
        self.assertNotIn(refresh, dump)

        # A different key cannot decrypt.
        other = ChannelCredentialService([Fernet.generate_key().decode()])
        with self.assertRaises(Exception):
            other.decrypt(row["access_token_encrypted"])

    def test_key_rotation(self):
        old = ChannelCredentialService([self.test_key])
        ciphertext = old.encrypt("rotate-me")

        new_key = Fernet.generate_key().decode()
        rotated_service = ChannelCredentialService([new_key, self.test_key])
        self.assertEqual(rotated_service.decrypt(ciphertext), "rotate-me")

        rotated = rotated_service.rotate(ciphertext)
        self.assertEqual(ChannelCredentialService([new_key]).decrypt(rotated), "rotate-me")

    def test_missing_or_invalid_key_fails_closed(self):
        original = settings.channel_credential_keys
        try:
            for bad in ("", "not-a-valid-fernet-key"):
                with self.subTest(key=bad or "<empty>"):
                    settings.channel_credential_keys = bad

                    response = self.create(self.owner, {
                        "channel_type": "facebook", "name": "No Key",
                        "access_token": "plaintext-should-not-be-stored",
                    })
                    self.assertEqual(response.status_code, 503)
                    self.assertNotIn("plaintext-should-not-be-stored", response.text)
                    self.assertEqual(
                        self.db.query(ChannelConnection).filter_by(name="No Key").count(), 0
                    )

                    # Channels without credentials still work.
                    response = self.create(self.owner, {
                        "channel_type": "facebook", "name": f"Plain {uuid.uuid4().hex[:4]}",
                    })
                    self.assertEqual(response.status_code, 201)
        finally:
            settings.channel_credential_keys = original

    def test_34_secrets_not_logged(self):
        handler = _CaptureHandler()
        root = logging.getLogger()
        previous_level = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            access = f"access-{uuid.uuid4().hex}"
            refresh = f"refresh-{uuid.uuid4().hex}"
            channel_id = self.create_with_credentials(access, refresh).json()["id"]
            headers = self.auth(self.owner, self.tenant_a)
            self.client.get(self.url(channel_id), headers=headers)
            self.client.post(self.url(channel_id, "/disconnect"), headers=headers)
            self.client.delete(self.url(channel_id), headers=headers)

            original = settings.channel_credential_keys
            settings.channel_credential_keys = ""
            try:
                self.create(self.owner, {
                    "channel_type": "facebook", "name": "No Key Log",
                    "access_token": access,
                })
            finally:
                settings.channel_credential_keys = original
        finally:
            root.removeHandler(handler)
            root.setLevel(previous_level)

        self.assertTrue(handler.messages, "expected log output to inspect")
        logged = "\n".join(handler.messages)
        self.assertNotIn(access, logged)
        self.assertNotIn(refresh, logged)
        self.assertNotIn(self.test_key, logged)


class ProviderTests(ChannelTestCase):

    def test_every_channel_type_has_provider(self):
        for channel_type in ChannelType:
            with self.subTest(channel_type=channel_type):
                provider = get_provider(channel_type)
                self.assertEqual(provider.channel_type, channel_type)
                self.assertEqual(get_provider(channel_type.value), provider)

    def test_no_provider_is_an_unimplemented_stub(self):
        # All four channel types are implemented now (WhatsApp, Facebook,
        # Instagram and Web Chat); no provider may silently fake success via
        # the UnimplementedChannelProvider placeholder.
        from app.integrations.base import UnimplementedChannelProvider
        for channel_type in ChannelType:
            provider = get_provider(channel_type)
            with self.subTest(channel_type=channel_type):
                self.assertNotIsInstance(provider, UnimplementedChannelProvider)

    def test_credentials_repr_hides_tokens(self):
        credentials = ProviderCredentials(access_token="secret-access", refresh_token="secret-refresh")
        self.assertNotIn("secret-access", repr(credentials))
        self.assertNotIn("secret-refresh", repr(credentials))


class WebhookRoutingTests(ChannelTestCase):

    def test_find_connected_channel(self):
        found = channel_service.find_connected_channel(self.db, ChannelType.WHATSAPP, "1001")
        self.assertEqual(found.id, self.wa_a.id)
        self.assertEqual(found.tenant_id, self.tenant_a.id)

        # Pending, wrong type, unknown: not routable.
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.INSTAGRAM, "ig_2002"))
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.INSTAGRAM, "1001"))
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.WHATSAPP, "unknown"))

    def test_inactive_channel_or_tenant_not_routable(self):
        self.wa_a.is_active = False
        self.db.commit()
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.WHATSAPP, "1001"))

        self.tenant_b.is_active = False
        self.db.commit()
        self.assertIsNone(channel_service.find_connected_channel(
            self.db, ChannelType.WHATSAPP, "9009"))
