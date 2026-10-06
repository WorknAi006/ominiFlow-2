"""
Tests for WhatsApp media download, storage and the authenticated media
endpoint.
"""
import hashlib
import logging
import re
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import httpx

from app.core.config import settings
from app.integrations.meta.graph_client import build_graph_client
from app.models import ChannelConnection, Message, MessageMedia
from app.services import media_service
from app.services.media_service import MediaOutcome
from app.services.whatsapp_event_processor import process_event
from app.storage import StorageError
from app.storage.base import InvalidStorageKeyError
from app.storage.local import LocalFileStorage
from tests.inbox_fixtures import APP_SECRET, PHONE_ID_A, PHONE_ID_B, TOKEN_A, TOKEN_B, WABA_A, WABA_B, InboxTestCase
from tests.meta_fakes import FakeMedia, FakeMeta

JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-bytes" * 50
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"video" * 40
OGG = b"OggS" + b"audio" * 40
PDF = b"%PDF-1.7\n" + b"document" * 40

MEDIA_CASES = {
    "image": ("image/jpeg", JPEG, ".jpg", {"caption": "Photo"}),
    "video": ("video/mp4", MP4, ".mp4", {}),
    "audio": ("audio/ogg; codecs=opus", OGG, ".ogg", {"voice": True}),
    "document": ("application/pdf", PDF, ".pdf", {"filename": "Invoice March.pdf"}),
}


class _Logs(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(self.format(record) + (record.exc_text or ""))


class MediaTestCase(InboxTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._media_root = tempfile.TemporaryDirectory()
        cls._saved_media = (settings.media_local_root, settings.media_max_download_attempts)
        settings.media_local_root = cls._media_root.name
        settings.media_max_download_attempts = 3
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        settings.media_local_root, settings.media_max_download_attempts = cls._saved_media
        cls._media_root.cleanup()

    def setUp(self) -> None:
        super().setUp()
        self.meta = FakeMeta(APP_SECRET, tokens={TOKEN_A: {WABA_A}, TOKEN_B: {WABA_B}})
        transport = httpx.MockTransport(self.meta.handler)
        self.provider.client_factory = lambda: build_graph_client(transport=transport)

    # ---------- helpers ----------

    def inbound_media(self, kind, mime, data, extra=None, channel=None, media_id=None, message_id=None, **fake):
        channel = channel or self.wa_a
        media_id = media_id or f"media-{uuid.uuid4().hex[:12]}"
        self.meta.add_media(media_id, FakeMedia(
            data=data, mime_type=mime, phone_number_id=channel.external_account_id, **fake,
        ))
        message = self.text_message(message_id, type=kind, **{kind: {"id": media_id, "mime_type": mime, **(extra or {})}})
        message.pop("text")
        event = self.message_event(channel, message)

        session = self.make_session()
        try:
            self.assertEqual(process_event(session, event.id), "processed")
        finally:
            session.close()

        self.db.expire_all()
        return self.db.query(MessageMedia).filter_by(provider_media_id=media_id).one()

    def download(self, media):
        session = self.make_session()
        try:
            return media_service.download_media(session, media.id)
        finally:
            session.close()

    def reset_lease(self, media):
        row = self.reload(MessageMedia, media.id)
        row.last_attempt_at = None
        self.db.commit()

    def stored_path(self, media) -> Path:
        return Path(settings.media_local_root) / self.reload(MessageMedia, media.id).storage_key

    def media_url(self, message_id):
        return f"/api/v1/messages/{message_id}/media"


class MediaDownloadTests(MediaTestCase):

    def test_download_each_media_kind(self):
        for kind, (mime, data, extension, extra) in MEDIA_CASES.items():
            with self.subTest(kind=kind):
                media = self.inbound_media(kind, mime, data, extra)
                self.assertEqual(media.status, "pending")
                self.assertEqual(media.media_kind, kind)

                self.assertEqual(self.download(media), MediaOutcome.DOWNLOADED)

                row = self.reload(MessageMedia, media.id)
                self.assertEqual(row.status, "downloaded")
                self.assertEqual(row.mime_type, mime.split(";")[0])
                self.assertEqual(row.file_size, len(data))
                self.assertEqual(row.sha256, hashlib.sha256(data).hexdigest())
                self.assertEqual(row.storage_backend, "local")
                self.assertRegex(
                    row.storage_key,
                    rf"^tenants/{self.tenant_a.id.hex}/messages/{row.message_id.hex}/[0-9a-f]{{32}}\{extension}$",
                )
                self.assertEqual(self.stored_path(media).read_bytes(), data)

                message = self.reload(Message, row.message_id)
                self.assertEqual(message.media_url, self.media_url(message.id))
                self.assertEqual(message.media_type, mime.split(";")[0])

                response = self.client.get(self.media_url(message.id), headers=self.auth(self.viewer, self.tenant_a))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, data)
                self.assertEqual(response.headers["content-type"].split(";")[0], mime.split(";")[0])
                self.assertEqual(response.headers["x-content-type-options"], "nosniff")
                self.assertIn("no-store", response.headers["cache-control"])
                expected_disposition = "attachment" if kind == "document" else "inline"
                self.assertTrue(response.headers["content-disposition"].startswith(expected_disposition))

        document = self.db.query(MessageMedia).filter_by(media_kind="document").one()
        self.assertEqual(document.original_filename, "Invoice March.pdf")

    def test_invalid_mime_rejected(self):
        for mime in ("image/svg+xml", "text/html", "application/x-msdownload"):
            with self.subTest(mime=mime):
                media = self.inbound_media("image", mime, b"<svg onload=alert(1)>")
                self.assertEqual(self.download(media), MediaOutcome.FAILED)
                row = self.reload(MessageMedia, media.id)
                self.assertEqual(row.error, "Unsupported media type.")
                self.assertIsNone(row.storage_key)
                self.assertEqual(row.attempts, 1)

    def test_content_type_mismatch_and_integrity(self):
        media = self.inbound_media("image", "image/jpeg", JPEG, content_type="text/html")
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).error, "Downloaded media type does not match.")

        media = self.inbound_media("image", "image/jpeg", JPEG, sha256="0" * 64)
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).error, "Media integrity check failed.")

    def test_oversized_media(self):
        # Declared too large: rejected before any download.
        media = self.inbound_media("image", "image/jpeg", JPEG, file_size=6 * 1024 * 1024)
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).error, "Media exceeds the size limit.")
        self.assertFalse(any(r.url.host == "lookaside.fbsbx.com" for r in self.meta.requests))

        # Declared small, but the body is larger: aborted while streaming.
        big = b"\xff\xd8" + b"x" * (5 * 1024 * 1024)
        media = self.inbound_media("image", "image/jpeg", big, file_size=100, sha256="")
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).error, "Media exceeds the size limit.")
        self.assertIsNone(self.reload(MessageMedia, media.id).storage_key)

    def test_download_timeout_retries_then_fails(self):
        media = self.inbound_media("video", "video/mp4", MP4)
        self.meta.download_timeout = True

        for attempt in (1, 2):
            with self.subTest(attempt=attempt):
                self.assertEqual(self.download(media), MediaOutcome.RETRY)
                row = self.reload(MessageMedia, media.id)
                self.assertEqual((row.status, row.attempts), ("pending", attempt))
                self.assertEqual(row.error, "Could not reach WhatsApp. Please try again later.")
                # Lease prevents an immediate second claim.
                self.assertEqual(self.download(media), MediaOutcome.SKIPPED)
                self.reset_lease(media)

        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).status, "failed")

    def test_provider_failures(self):
        media = self.inbound_media("image", "image/jpeg", JPEG)
        self.meta.graph_error = (400, "Media expired for token {token}", 131052)
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        error = self.reload(MessageMedia, media.id).error
        self.assertIn("WhatsApp media request failed", error)
        self.assertIn("[redacted]", error)
        self.assertNotIn(TOKEN_A, error)

        media = self.inbound_media("image", "image/jpeg", JPEG)
        self.meta.graph_error = (500, "boom", 1)
        self.assertEqual(self.download(media), MediaOutcome.RETRY)

        self.meta.graph_error = None
        media = self.inbound_media("image", "image/jpeg", JPEG, download_status=403)
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertIn("HTTP 403", self.reload(MessageMedia, media.id).error)

    def test_untrusted_download_urls_never_receive_token(self):
        for url in (
            "https://evil.example.com/steal",
            "http://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=x",
            "https://lookaside.fbsbx.com.evil.com/x",
            "https://user:pass@lookaside.fbsbx.com/x",
            "https://lookaside.fbsbx.com:8443/x",
        ):
            with self.subTest(url=url):
                media = self.inbound_media("image", "image/jpeg", JPEG, url=url)
                self.assertEqual(self.download(media), MediaOutcome.FAILED)
                self.assertIn("Untrusted media download URL", self.reload(MessageMedia, media.id).error)

        self.assertEqual(self.meta.untrusted_requests, [])

    def test_storage_failure_is_retried(self):
        media = self.inbound_media("image", "image/jpeg", JPEG)
        with mock.patch.object(LocalFileStorage, "save", side_effect=StorageError("Media could not be stored.")):
            self.assertEqual(self.download(media), MediaOutcome.RETRY)
        row = self.reload(MessageMedia, media.id)
        self.assertEqual((row.status, row.error), ("pending", "Media could not be stored."))
        self.assertIsNone(self.reload(Message, row.message_id).media_url)

        self.reset_lease(media)
        self.assertEqual(self.download(media), MediaOutcome.DOWNLOADED)

    def test_disconnected_channel_fails_safely(self):
        media = self.inbound_media("image", "image/jpeg", JPEG)
        self.client.post(f"/api/v1/channels/{self.wa_a.id}/disconnect", headers=self.auth(self.owner, self.tenant_a))
        self.assertEqual(self.download(media), MediaOutcome.FAILED)
        self.assertEqual(self.reload(MessageMedia, media.id).error, "Channel credentials are unavailable.")
        # Restore for other assertions in this class.
        channel = self.reload(ChannelConnection, self.wa_a.id)
        self.assertEqual(channel.status, "disconnected")

    def test_media_bound_to_its_phone_number(self):
        # Media id belongs to tenant B's number; requesting it via A fails.
        media = self.inbound_media("image", "image/jpeg", JPEG)
        self.meta.media[media.provider_media_id].phone_number_id = PHONE_ID_B
        self.assertEqual(self.download(media), MediaOutcome.FAILED)

    def test_duplicate_event_does_not_duplicate_media(self):
        self.inbound_media("image", "image/jpeg", JPEG, media_id="media-dup", message_id="wamid.media-dup")
        message = self.text_message("wamid.media-dup", type="image", image={"id": "media-dup", "mime_type": "image/jpeg"})
        message.pop("text")
        replay = self.message_event(self.wa_a, message, dedupe_key="message:replay")
        session = self.make_session()
        try:
            process_event(session, replay.id)
        finally:
            session.close()
        self.assertEqual(self.db.query(MessageMedia).filter_by(provider_media_id="media-dup").count(), 1)
        self.assertEqual(self.db.query(Message).filter_by(external_message_id="wamid.media-dup").count(), 1)

    def test_process_pending_media(self):
        self.inbound_media("image", "image/jpeg", JPEG)
        self.inbound_media("document", "application/pdf", PDF)
        self.inbound_media("image", "text/html", b"<html>")
        session = self.make_session()
        try:
            self.assertEqual(media_service.process_pending_media(session), {"downloaded": 2, "failed": 1})
            self.assertEqual(media_service.process_pending_media(session), {})
        finally:
            session.close()

    def test_tokens_never_logged_or_exposed(self):
        handler = _Logs()
        root = logging.getLogger()
        previous = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            ok = self.inbound_media("image", "image/jpeg", JPEG)
            self.download(ok)
            self.meta.graph_error = (400, "bad token {token}", 190)
            self.download(self.inbound_media("image", "image/jpeg", JPEG))
        finally:
            root.removeHandler(handler)
            root.setLevel(previous)

        logged = "\n".join(handler.messages)
        self.assertNotIn(TOKEN_A, logged)
        self.assertNotIn("hash=sig", logged)  # provider URL never logged

        message = self.reload(Message, ok.message_id)
        response = self.client.get(f"/api/v1/messages/{message.id}", headers=self.auth(self.owner, self.tenant_a))
        for secret in (TOKEN_A, "lookaside", "fbsbx", "hash=sig"):
            self.assertNotIn(secret, response.text)
        self.assertEqual(response.json()["media_url"], self.media_url(message.id))


class MediaEndpointTests(MediaTestCase):

    def test_tenant_isolation_and_states(self):
        media = self.inbound_media("image", "image/jpeg", JPEG)
        url = self.media_url(media.message_id)

        # Pending: not available yet.
        self.assertEqual(self.client.get(url, headers=self.auth(self.owner, self.tenant_a)).status_code, 409)
        self.download(media)

        self.assertEqual(self.client.get(url, headers=self.auth(self.owner, self.tenant_a)).status_code, 200)
        self.assertEqual(self.client.get(url, headers=self.auth(self.owner_b, self.tenant_b)).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(self.media_url(uuid.uuid4()), headers=self.auth(self.owner, self.tenant_a)).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/messages/x/media", headers=self.auth(self.owner, self.tenant_a)).status_code, 422)

        # Text message without media.
        text_event = self.message_event(self.wa_a, self.text_message())
        session = self.make_session()
        try:
            process_event(session, text_event.id)
        finally:
            session.close()
        text_message = self.db.query(Message).filter_by(message_type="text").one()
        self.assertEqual(
            self.client.get(self.media_url(text_message.id), headers=self.auth(self.owner, self.tenant_a)).status_code,
            404,
        )

        # Tenant B's media is not reachable from tenant A.
        media_b = self.inbound_media("image", "image/jpeg", JPEG, channel=self.wa_b)
        self.download(media_b)
        self.assertEqual(
            self.client.get(self.media_url(media_b.message_id), headers=self.auth(self.owner, self.tenant_a)).status_code,
            404,
        )
        self.assertTrue(self.reload(MessageMedia, media_b.id).storage_key.startswith(f"tenants/{self.tenant_b.id.hex}/"))

    def test_failed_media_not_served(self):
        media = self.inbound_media("image", "text/html", b"<html>")
        self.download(media)
        response = self.client.get(self.media_url(media.message_id), headers=self.auth(self.owner, self.tenant_a))
        self.assertEqual(response.status_code, 409)


class SafeFilenameAndStorageTests(MediaTestCase):

    def test_safe_filenames(self):
        cases = {
            "../../etc/passwd": "passwd.pdf",
            "..\\..\\windows\\system32\\evil.exe": "evil.pdf",
            "report<script>.pdf": "report_script_.pdf",
            "   ": None,
            ".hidden": "hidden.pdf",
            "a" * 300 + ".pdf": "a" * 100 + ".pdf",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw[:30]):
                self.assertEqual(media_service.sanitize_filename(raw, ".pdf"), expected)

    def test_provider_filename_never_used_for_storage(self):
        media = self.inbound_media("document", "application/pdf", PDF, extra={"filename": "../../../../tmp/pwned.sh"})
        self.download(media)
        row = self.reload(MessageMedia, media.id)
        self.assertEqual(row.original_filename, "pwned.pdf")
        self.assertNotIn("pwned", row.storage_key)
        self.assertTrue(self.stored_path(media).resolve().is_relative_to(Path(settings.media_local_root).resolve()))

    def test_path_traversal_keys_rejected(self):
        storage = LocalFileStorage(settings.media_local_root)
        for key in ("../escape.txt", "/etc/passwd", "tenants/../../escape", "tenants\\..\\x",
                    "", "Tenants/upper", "tenants//double", "tenants/./x", "c:/windows"):
            with self.subTest(key=key):
                with self.assertRaises(InvalidStorageKeyError):
                    storage.save(key, b"x", "text/plain")
        self.assertFalse((Path(settings.media_local_root).parent / "escape.txt").exists())

    def test_storage_roundtrip(self):
        storage = LocalFileStorage(settings.media_local_root)
        key = f"tenants/{uuid.uuid4().hex}/messages/{uuid.uuid4().hex}/file.pdf"
        storage.save(key, b"hello", "application/pdf")
        self.assertTrue(storage.exists(key))
        self.assertEqual(b"".join(storage.iter_chunks(key)), b"hello")
        storage.delete(key)
        self.assertFalse(storage.exists(key))
        self.assertFalse(re.search(r"\.upload-", " ".join(p.name for p in Path(settings.media_local_root).rglob("*"))))
