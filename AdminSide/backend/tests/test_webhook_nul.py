"""
Tests for NUL (U+0000) handling in WhatsApp webhook payloads: the
sanitizer itself, and end-to-end storage in PostgreSQL through the signed
webhook endpoint.
"""
import copy
import hashlib
import hmac
import json
import logging
import unittest
from unittest import mock

from sqlalchemy.exc import DataError

from app.core.json_sanitize import strip_nul
from app.models import ChannelStatus, ChannelType, Contact, Message, WhatsAppEvent
from app.services.whatsapp_event_processor import process_pending_events
from tests.test_whatsapp import APP_SECRET, WhatsAppTestCase

WEBHOOK_URL = "/api/v1/webhooks/whatsapp"
PHONE, WABA = "300000000000077", "400000000000077"
CUSTOMER = "15550102000"


# =========================
# SANITIZER
# =========================

class StripNulTests(unittest.TestCase):

    def test_top_level_string(self):
        self.assertEqual(strip_nul("a\x00b\x00"), ("ab", 2))
        self.assertEqual(strip_nul("clean"), ("clean", 0))

    def test_nested_dict_values(self):
        value = {"entry": {"changes": {"value": {"text": "hi\x00there"}}}}
        self.assertEqual(strip_nul(value), ({"entry": {"changes": {"value": {"text": "hithere"}}}}, 1))

    def test_list_elements(self):
        value = ["a\x00", ["b\x00\x00", {"c": ["\x00d"]}], 5]
        self.assertEqual(strip_nul(value), (["a", ["b", {"c": ["d"]}], 5], 4))

    def test_object_keys(self):
        cleaned, removed = strip_nul({"na\x00me": "x", "id": 1})
        self.assertEqual((cleaned, removed), ({"name": "x", "id": 1}, 1))

        # An originally clean key always wins, regardless of order.
        self.assertEqual(strip_nul({"k\x00": "dirty", "k": "clean"})[0], {"k": "clean"})
        self.assertEqual(strip_nul({"k": "clean", "k\x00": "dirty"})[0], {"k": "clean"})
        # Two dirty keys: the first wins.
        self.assertEqual(strip_nul({"k\x00": "first", "\x00k": "second"})[0], {"k": "first"})

    def test_unicode_and_emoji_preserved(self):
        text = "नमस्कार, तुमची ऑर्डर तयार आहे 🙏 नमस्ते 😀 👍🏽 مرحبا 你好"
        self.assertEqual(strip_nul({"t": text}), ({"t": text}, 0))
        self.assertEqual(strip_nul(f"नमस्कार\x00 🙏"), ("नमस्कार 🙏", 1))

    def test_whitespace_and_other_control_characters_preserved(self):
        text = "line 1\nline 2\r\n\ttabbed \x1b\x07"
        self.assertEqual(strip_nul(text), (text, 0))

    def test_scalars_and_input_untouched(self):
        value = {"n": 1, "f": 1.5, "b": True, "z": None, "s": "x\x00"}
        original = copy.deepcopy(value)
        cleaned, _ = strip_nul(value)
        self.assertEqual(cleaned, {"n": 1, "f": 1.5, "b": True, "z": None, "s": "x"})
        self.assertEqual(value, original)
        for scalar in (0, 2.5, False, None):
            self.assertEqual(strip_nul(scalar), (scalar, 0))

    def test_deep_nesting_does_not_recurse(self):
        root = current = []
        for _ in range(20000):
            child = []
            current.append(child)
            current = child
        current.append("deep\x00")
        cleaned, removed = strip_nul(root)
        self.assertEqual(removed, 1)


# =========================
# WEBHOOK -> POSTGRESQL
# =========================

def sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def webhook(message_id="wamid.NUL1", body="Hello\x00 world", profile="Ja\x00ne", sender=CUSTOMER, extra_key=False):
    message = {
        "from": sender,
        "id": message_id,
        "timestamp": "1767225600",
        "type": "text",
        "text": {"body": body},
    }
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550100", "phone_number_id": PHONE},
        "contacts": [{"wa_id": CUSTOMER, "profile": {"name": profile}}],
        "messages": [message],
    }
    if extra_key:
        value["cust\x00om_key"] = "x"
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": WABA, "changes": [{"field": "messages", "value": value}]}],
    }


class _AppLogs(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("app."):
            self.messages.append(self.format(record) + (record.exc_text or ""))

    def __enter__(self):
        root = logging.getLogger()
        self._level = root.level
        root.addHandler(self)
        root.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *exc):
        root = logging.getLogger()
        root.removeHandler(self)
        root.setLevel(self._level)


class WebhookNulTests(WhatsAppTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.channel = cls.make_channel(
            cls.tenant_a, ChannelType.WHATSAPP, "NUL channel",
            status=ChannelStatus.CONNECTED,
            external_account_id=PHONE, external_business_id=WABA,
        )

    def post_raw(self, raw: bytes, signature: str | None = None):
        return self.client.post(
            WEBHOOK_URL,
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature if signature is not None else sign(raw),
            },
        )

    def post(self, payload: dict):
        # json.dumps writes NUL as the legal JSON escape "\u0000".
        raw = json.dumps(payload).encode()
        self.assertIn(b"\\u0000", raw)
        return self.post_raw(raw)

    def events(self):
        self.db.expire_all()
        return self.db.query(WhatsAppEvent).filter_by(channel_id=self.channel.id).all()

    def test_nul_payload_is_stored_and_processed(self):
        response = self.post(webhook(sender="1555010\x002000", message_id="wamid.N\x00UL1", extra_key=True))
        self.assertEqual(response.status_code, 200, response.text)

        [event] = self.events()
        stored = json.dumps(event.payload)
        self.assertNotIn("\\u0000", stored)
        self.assertEqual(event.wa_message_id, "wamid.NUL1")
        self.assertEqual(event.wa_id, CUSTOMER)
        self.assertEqual(event.payload["message"]["text"]["body"], "Hello world")
        self.assertEqual(event.payload["contact"]["profile"]["name"], "Jane")

        session = self.make_session()
        try:
            self.assertEqual(process_pending_events(session), {"processed": 1})
        finally:
            session.close()

        self.db.expire_all()
        message = self.db.query(Message).filter_by(external_message_id="wamid.NUL1").one()
        self.assertEqual(message.text, "Hello world")
        contact = self.db.get(Contact, message.contact_id)
        self.assertEqual((contact.profile_name, contact.normalized_phone_number), ("Jane", f"+{CUSTOMER}"))

    def test_unicode_survives_storage(self):
        body = "नमस्कार 🙏\nतुमची ऑर्डर\tतयार आहे 😀"
        self.assertEqual(self.post(webhook(body=body + "\x00")).status_code, 200)
        [event] = self.events()
        self.assertEqual(event.payload["message"]["text"]["body"], body)

    def test_duplicates_still_deduplicated(self):
        # Same message delivered three times, with NUL inside its id.
        with _AppLogs() as logs:
            self.assertEqual(self.post(webhook(message_id="wamid.DUP\x00")).status_code, 200)
            self.assertEqual(self.post(webhook(message_id="wamid.DUP", body="x\x00")).status_code, 200)
            self.assertEqual(self.post(webhook(message_id="wamid.DUP\x00")).status_code, 200)
        self.assertEqual([e.wa_message_id for e in self.events()], ["wamid.DUP"])

        # Accounting is correct: one stored, then two duplicates.
        processed = [m for m in logs.messages if "webhook processed" in m]
        self.assertEqual(len(processed), 3)
        self.assertIn("stored=1 duplicates=0", processed[0])
        self.assertTrue(all("stored=0 duplicates=1" in m for m in processed[1:]))

    def test_signature_verified_on_original_bytes(self):
        raw = json.dumps(webhook()).encode()

        # Signature of the original bytes (with the \u0000 escape) is valid.
        self.assertEqual(self.post_raw(raw).status_code, 200)

        # A signature computed over a NUL-free version does NOT validate the
        # original bytes: sanitization never happens before verification.
        sanitized = json.dumps(strip_nul(webhook(message_id="wamid.OTHER"))[0]).encode()
        raw_other = json.dumps(webhook(message_id="wamid.OTHER")).encode()
        self.assertEqual(self.post_raw(raw_other, signature=sign(sanitized)).status_code, 403)
        self.assertEqual(len(self.events()), 1)

    def test_rejections_unchanged(self):
        raw = json.dumps(webhook()).encode()
        self.assertEqual(self.post_raw(raw, signature="sha256=" + "0" * 64).status_code, 403)
        self.assertEqual(self.post_raw(raw, signature="").status_code, 403)

        # A raw (unescaped) NUL byte is invalid JSON: still 400.
        invalid = b'{"object": "whatsapp_business_account", "x": "a\x00b"}'
        self.assertEqual(self.post_raw(invalid).status_code, 400)
        self.assertEqual(self.post_raw(b"{not json").status_code, 400)

        self.assertEqual(self.events(), [])

    def test_logs_do_not_contain_payload_or_secrets(self):
        raw = json.dumps(webhook(body="private customer text\x00", profile="Jane")).encode()
        signature = sign(raw)
        with _AppLogs() as logs:
            self.assertEqual(self.post_raw(raw, signature=signature).status_code, 200)

        joined = "\n".join(logs.messages)
        self.assertIn("Removed 1 NUL character(s)", joined)
        self.assertIn("stored=1 duplicates=0", joined)
        for secret in ("private customer text", "Jane", CUSTOMER, APP_SECRET, signature):
            self.assertNotIn(secret, joined)

    def test_database_error_logs_no_payload(self):
        error = DataError(
            "INSERT INTO whatsapp_events ...",
            {"payload": "private customer text", "wa_id": CUSTOMER},
            Exception("unsupported Unicode escape sequence"),
        )
        with _AppLogs() as logs, mock.patch(
            "app.services.whatsapp_service._store_event", side_effect=error,
        ):
            response = self.post(webhook())

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Webhook processing failed."})
        joined = "\n".join(logs.messages)
        self.assertIn("Database error while storing WhatsApp webhook: DataError", joined)
        self.assertNotIn("private customer text", joined)
        self.assertNotIn(CUSTOMER, joined)
