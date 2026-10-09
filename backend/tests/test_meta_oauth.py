"""
Tenant self-service Meta OAuth onboarding (Facebook + Instagram):
secure state, server-side code exchange, asset discovery, tenant/user
binding, replay/expiry protection, connection creation, reconnect,
duplicate conflicts, and webhook compatibility. Uses a fake Meta Graph
transport; no live Meta calls and no real credentials.
"""
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings
from app.integrations.meta.graph_client import appsecret_proof, build_graph_client
from app.integrations.registry import get_provider
from app.models import ChannelConnection, ChannelStatus, ChannelType, OAuthState, OAuthStatus
from app.services import channel_service, meta_oauth_service
from app.services.meta_oauth_service import _utcnow
from tests.base import DatabaseTestCase

APP_ID = "555666777888"
APP_SECRET = f"oauth-secret-{uuid.uuid4().hex}"

PAGE_FB = "700000000000001"       # Facebook page (also linked to IG below)
PAGE_PLAIN = "700000000000002"    # Facebook page with no Instagram account
IG_ID = "17800000000000001"       # Instagram professional account id


def _err(status_code, message, code):
    return httpx.Response(status_code, json={"error": {"message": message, "code": code}})


class FakeMetaOAuth:
    """Fake Graph endpoints for the OAuth flow and provider finalization."""

    def __init__(self):
        self.requests = []
        self.subscribed = set()
        self.pages = [
            {"id": PAGE_FB, "name": "OnlineGo Page", "access_token": "PT_FB",
             "instagram_business_account": {"id": IG_ID, "username": "onlinego", "name": "OnlineGo"}},
            {"id": PAGE_PLAIN, "name": "Side Page", "access_token": "PT_PLAIN"},
        ]
        self.no_pages = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host != "graph.facebook.com":
            return httpx.Response(200, content=b"stolen")
        _, _, path = request.url.path.lstrip("/").partition("/")
        params = request.url.params
        token = request.headers.get("authorization", "").removeprefix("Bearer ")

        # OAuth token exchange + long-lived exchange (no bearer, client creds).
        if path == "oauth/access_token":
            if params.get("grant_type") == "fb_exchange_token":
                return httpx.Response(200, json={"access_token": "LL_USER_TOKEN", "token_type": "bearer", "expires_in": 5184000})
            if params.get("code"):
                return httpx.Response(200, json={"access_token": "USER_TOKEN", "token_type": "bearer", "expires_in": 3600})
            return _err(400, "Missing code", 100)

        # debug_token uses the app token, no appsecret_proof.
        if path == "debug_token":
            return httpx.Response(200, json={"data": {
                "is_valid": True, "app_id": APP_ID, "expires_at": 0,
                "scopes": ["pages_show_list", "pages_messaging", "pages_manage_metadata",
                           "instagram_basic", "instagram_manage_messages"],
            }})

        # Every other call carries a user/page token and an appsecret_proof.
        if params.get("appsecret_proof") != appsecret_proof(APP_SECRET, token):
            return _err(400, "Invalid appsecret_proof", 100)

        if path == "me/accounts":
            return httpx.Response(200, json={"data": [] if self.no_pages else self.pages})

        parts = path.split("/")
        if len(parts) == 2 and parts[1] == "subscribed_apps":
            page_id = parts[0]
            if request.method == "POST":
                self.subscribed.add(page_id)
                return httpx.Response(200, json={"success": True})
            data = [{"id": APP_ID, "subscribed_fields": [{"name": "messages"}]}] if page_id in self.subscribed else []
            return httpx.Response(200, json={"data": data})

        if len(parts) == 1:
            page_id = parts[0]
            page = next((p for p in self.pages if p["id"] == page_id), None)
            fields = params.get("fields", "")
            if "instagram_business_account" in fields:
                body = {"id": page_id}
                if page and page.get("instagram_business_account"):
                    body["instagram_business_account"] = page["instagram_business_account"]
                return httpx.Response(200, json=body)
            return httpx.Response(200, json={"id": page_id, "name": page["name"] if page else "Page"})

        return _err(404, "Unknown path", 100)


class MetaOAuthTestCase(DatabaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls._saved = {n: getattr(settings, n) for n in (
            "meta_app_id", "meta_app_secret", "channel_credential_keys",
            "frontend_url", "meta_oauth_redirect_uri",
        )}
        settings.meta_app_id = APP_ID
        settings.meta_app_secret = APP_SECRET
        settings.channel_credential_keys = Fernet.generate_key().decode()
        settings.frontend_url = "http://localhost:3000"
        settings.meta_oauth_redirect_uri = "http://localhost:8000/api/v1/channels/oauth/callback"
        cls.fb_provider = get_provider(ChannelType.FACEBOOK)
        cls.ig_provider = get_provider(ChannelType.INSTAGRAM)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.fb_provider.client_factory = build_graph_client
        cls.ig_provider.client_factory = build_graph_client
        for n, v in cls._saved.items():
            setattr(settings, n, v)

    def setUp(self):
        super().setUp()
        self.fake = FakeMetaOAuth()
        transport = httpx.MockTransport(self.fake.handler)
        factory = lambda: build_graph_client(transport=transport)
        self.fb_provider.client_factory = factory
        self.ig_provider.client_factory = factory

    @classmethod
    def create_fixtures(cls):
        cls.tenant_a = cls.make_tenant("OnlineGo")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")
        cls.tenant_b = cls.make_tenant("AI Tourism")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

    # ---------- helpers ----------

    def auth_h(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def start(self, provider, actor=None, tenant=None):
        resp = self.client.post(f"/api/v1/channels/oauth/{provider}/start", headers=self.auth_h(actor, tenant))
        return resp

    def state_from_url(self, url):
        return parse_qs(urlparse(url).query)["state"][0]

    def callback(self, state, code="auth_code_123", error=None):
        params = {"state": state}
        if code is not None:
            params["code"] = code
        if error is not None:
            params["error"] = error
        return self.client.get("/api/v1/channels/oauth/callback", params=params, follow_redirects=False)

    def selection_from_redirect(self, resp):
        q = parse_qs(urlparse(resp.headers["location"]).query)
        return q

    def run_oauth(self, provider, external_account_id, actor=None, tenant=None):
        started = self.start(provider, actor, tenant)
        self.assertEqual(started.status_code, 200, started.text)
        state = self.state_from_url(started.json()["authorization_url"])
        cb = self.callback(state)
        self.assertEqual(cb.status_code, 303)
        q = self.selection_from_redirect(cb)
        token = q["connect"][0]
        assets = self.client.get(f"/api/v1/channels/oauth/assets?token={token}", headers=self.auth_h(actor, tenant))
        self.assertEqual(assets.status_code, 200, assets.text)
        sel = self.client.post("/api/v1/channels/oauth/select", headers=self.auth_h(actor, tenant),
                               json={"token": token, "external_account_id": external_account_id})
        return token, assets, sel

    # ========== start / state security ==========

    def test_01_start_requires_auth_and_permission(self):
        self.assertEqual(self.client.post("/api/v1/channels/oauth/facebook/start").status_code, 401)
        self.assertEqual(self.start("facebook", actor=self.viewer).status_code, 403)

    def test_02_start_builds_dialog_url_and_secure_state(self):
        resp = self.start("facebook")
        self.assertEqual(resp.status_code, 200, resp.text)
        url = resp.json()["authorization_url"]
        self.assertTrue(url.startswith("https://www.facebook.com/"))
        q = parse_qs(urlparse(url).query)
        self.assertEqual(q["client_id"][0], APP_ID)
        self.assertEqual(q["response_type"][0], "code")
        self.assertIn("pages_messaging", q["scope"][0])
        state = q["state"][0]
        self.assertGreaterEqual(len(state), 20)
        row = self.db.query(OAuthState).filter_by(state_token=state).one()
        self.assertEqual((row.tenant_id, row.user_id, row.provider, row.status),
                         (self.tenant_a.id, self.owner.id, "facebook", "pending"))
        self.assertNotIn(APP_SECRET, url)

    def test_03_invalid_provider_rejected(self):
        self.assertEqual(self.start("whatsapp").status_code, 422)
        self.assertEqual(self.start("twitter").status_code, 422)

    # ========== callback ==========

    def test_04_callback_exchanges_code_server_side_and_redirects(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        cb = self.callback(state)
        self.assertEqual(cb.status_code, 303)
        q = self.selection_from_redirect(cb)
        self.assertIn("connect", q)
        self.assertEqual(q["provider"][0], "facebook")
        # A user/page token was never exposed in the redirect.
        self.assertNotIn("USER_TOKEN", cb.headers["location"])
        self.assertNotIn("PT_FB", cb.headers["location"])
        # The code exchange happened server-side.
        self.assertTrue(any("oauth/access_token" in str(r.url) for r in self.fake.requests))

    def test_05_callback_user_cancelled(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        cb = self.callback(state, code=None, error="access_denied")
        self.assertEqual(cb.status_code, 303)
        self.assertEqual(self.selection_from_redirect(cb)["connect_error"][0], "cancelled")

    def test_06_callback_invalid_state(self):
        cb = self.callback("not-a-real-state")
        self.assertEqual(self.selection_from_redirect(cb)["connect_error"][0], "invalid_state")

    def test_07_callback_state_single_use_replay_protected(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        self.assertIn("connect", self.selection_from_redirect(self.callback(state)))
        replay = self.callback(state)
        self.assertEqual(self.selection_from_redirect(replay)["connect_error"][0], "invalid_state")

    def test_08_callback_expired_state(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        row = self.db.query(OAuthState).filter_by(state_token=state).one()
        row.expires_at = _utcnow() - timedelta(minutes=1)
        self.db.commit()
        cb = self.callback(state)
        self.assertEqual(self.selection_from_redirect(cb)["connect_error"][0], "expired")

    def test_09_callback_no_pages(self):
        self.fake.no_pages = True
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        cb = self.callback(state)
        self.assertEqual(self.selection_from_redirect(cb)["connect_error"][0], "no_pages")

    def test_10_callback_no_instagram(self):
        self.fake.pages = [{"id": PAGE_PLAIN, "name": "Side Page", "access_token": "PT_PLAIN"}]
        state = self.state_from_url(self.start("instagram").json()["authorization_url"])
        cb = self.callback(state)
        self.assertEqual(self.selection_from_redirect(cb)["connect_error"][0], "no_instagram")

    # ========== assets ==========

    def test_11_assets_returns_safe_metadata_only(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        token = self.selection_from_redirect(self.callback(state))["connect"][0]
        resp = self.client.get(f"/api/v1/channels/oauth/assets?token={token}", headers=self.auth_h())
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["provider"], "facebook")
        ids = {a["external_account_id"] for a in body["assets"]}
        self.assertEqual(ids, {PAGE_FB, PAGE_PLAIN})
        self.assertNotIn("PT_FB", resp.text)
        self.assertNotIn("access_token", resp.text)

    def test_12_assets_cross_tenant_denied(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        token = self.selection_from_redirect(self.callback(state))["connect"][0]
        # Tenant B cannot read Tenant A's selection session.
        resp = self.client.get(f"/api/v1/channels/oauth/assets?token={token}", headers=self.auth_h(self.owner_b, self.tenant_b))
        self.assertEqual(resp.status_code, 400)

    # ========== select / connection creation ==========

    def test_13_facebook_connection_created_with_encrypted_credentials(self):
        _, _, sel = self.run_oauth("facebook", PAGE_FB)
        self.assertEqual(sel.status_code, 200, sel.text)
        body = sel.json()
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["external_account_id"], PAGE_FB)
        self.assertTrue(body["has_credentials"])
        self.assertNotIn("PT_FB", sel.text)
        self.assertIn(PAGE_FB, self.fake.subscribed)
        channel = self.db.query(ChannelConnection).filter_by(
            tenant_id=self.tenant_a.id, channel_type="facebook", external_account_id=PAGE_FB).one()
        self.assertNotIn("PT_FB", channel.access_token_encrypted or "")

    def test_14_instagram_connection_created_with_page_linkage(self):
        _, assets, sel = self.run_oauth("instagram", IG_ID)
        self.assertEqual(assets.json()["assets"][0]["page_id"], PAGE_FB)  # linked page surfaced
        self.assertEqual(sel.status_code, 200, sel.text)
        body = sel.json()
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["external_account_id"], IG_ID)
        self.assertEqual(body["external_business_id"], PAGE_FB)  # linked page stored
        self.assertIn(PAGE_FB, self.fake.subscribed)

    def test_15_select_token_single_use(self):
        token, _, sel = self.run_oauth("facebook", PAGE_FB)
        self.assertEqual(sel.status_code, 200)
        again = self.client.post("/api/v1/channels/oauth/select", headers=self.auth_h(),
                                 json={"token": token, "external_account_id": PAGE_FB})
        self.assertEqual(again.status_code, 400)

    def test_16_select_cross_tenant_denied(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        token = self.selection_from_redirect(self.callback(state))["connect"][0]
        resp = self.client.post("/api/v1/channels/oauth/select", headers=self.auth_h(self.owner_b, self.tenant_b),
                                json={"token": token, "external_account_id": PAGE_FB})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.db.query(ChannelConnection).filter_by(tenant_id=self.tenant_b.id).count(), 0)

    def test_17_reconnect_updates_existing_channel(self):
        _, _, first = self.run_oauth("facebook", PAGE_FB)
        channel_id = first.json()["id"]
        _, _, second = self.run_oauth("facebook", PAGE_FB)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["id"], channel_id)  # same channel, no duplicate
        self.assertEqual(self.db.query(ChannelConnection).filter_by(
            tenant_id=self.tenant_a.id, channel_type="facebook", external_account_id=PAGE_FB).count(), 1)

    def test_18_duplicate_connection_other_tenant_conflict(self):
        _, _, first = self.run_oauth("facebook", PAGE_FB)
        self.assertEqual(first.status_code, 200)
        # Tenant B tries to connect the same Page -> safe conflict, no leak.
        _, _, sel_b = self.run_oauth("facebook", PAGE_FB, actor=self.owner_b, tenant=self.tenant_b)
        self.assertEqual(sel_b.status_code, 409)
        self.assertNotIn("OnlineGo", sel_b.text)

    def test_19_webhook_routing_compatibility(self):
        self.run_oauth("facebook", PAGE_FB)
        self.run_oauth("instagram", IG_ID)
        fb = channel_service.find_connected_channel(self.db, ChannelType.FACEBOOK, PAGE_FB)
        ig = channel_service.find_connected_channel(self.db, ChannelType.INSTAGRAM, IG_ID)
        self.assertIsNotNone(fb)
        self.assertEqual(fb.tenant_id, self.tenant_a.id)
        self.assertIsNotNone(ig)
        self.assertEqual(ig.tenant_id, self.tenant_a.id)

    def test_20_select_invalid_account_rejected(self):
        state = self.state_from_url(self.start("facebook").json()["authorization_url"])
        token = self.selection_from_redirect(self.callback(state))["connect"][0]
        resp = self.client.post("/api/v1/channels/oauth/select", headers=self.auth_h(),
                                json={"token": token, "external_account_id": "999999999999999"})
        self.assertEqual(resp.status_code, 400)

    def test_21_state_consumed_after_connect(self):
        token, _, sel = self.run_oauth("facebook", PAGE_FB)
        self.assertEqual(sel.status_code, 200)
        row = self.db.query(OAuthState).filter_by(selection_token=token).one()
        self.assertEqual(row.status, OAuthStatus.CONSUMED)
        self.assertIsNone(row.user_token_encrypted)  # stored token cleared
