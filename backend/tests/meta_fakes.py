"""
Fake Meta endpoints for media and template tests (httpx.MockTransport):
Graph media info, CDN media download, paginated template list and the
messages endpoint.
"""
import hashlib
import json
import uuid
from dataclasses import dataclass, field

import httpx

from app.integrations.meta.graph_client import appsecret_proof

MEDIA_HOST = "lookaside.fbsbx.com"


@dataclass
class FakeMedia:
    data: bytes
    mime_type: str
    phone_number_id: str
    url: str | None = None
    sha256: str | None = None
    file_size: int | None = None
    content_type: str | None = None
    download_status: int = 200


@dataclass
class FakeMeta:
    app_secret: str
    tokens: dict[str, set[str]]          # token -> WABA ids it may access
    media: dict[str, FakeMedia] = field(default_factory=dict)
    templates: dict[str, list[dict]] = field(default_factory=dict)  # waba -> templates
    page_size: int = 3
    requests: list[httpx.Request] = field(default_factory=list)
    untrusted_requests: list[httpx.Request] = field(default_factory=list)
    graph_error: tuple[int, str, int] | None = None
    send_error: tuple[int, str, int] | None = None
    network_down: bool = False
    download_timeout: bool = False
    sent: list[dict] = field(default_factory=list)

    def add_media(self, media_id: str, item: FakeMedia) -> FakeMedia:
        item.url = item.url or f"https://{MEDIA_HOST}/whatsapp_business/attachments/?mid={media_id}&hash=sig"
        if item.sha256 is None:
            item.sha256 = hashlib.sha256(item.data).hexdigest()
        if item.file_size is None:
            item.file_size = len(item.data)
        self.media[media_id] = item
        return item

    @staticmethod
    def _error(status_code: int, message: str, code: int) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"message": message, "code": code}})

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if self.network_down:
            raise httpx.ConnectError("connection refused", request=request)

        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        host = request.url.host

        # ---- CDN download ----
        if host == MEDIA_HOST:
            if self.download_timeout:
                raise httpx.ReadTimeout("timed out", request=request)
            if token not in self.tokens:
                return httpx.Response(401)
            media_id = request.url.params.get("mid")
            item = self.media.get(media_id)
            if item is None:
                return httpx.Response(404)
            headers = {"content-type": item.content_type or item.mime_type}
            return httpx.Response(item.download_status, content=item.data, headers=headers)

        if host != "graph.facebook.com":
            self.untrusted_requests.append(request)
            return httpx.Response(200, content=b"stolen")

        # ---- Graph API ----
        if request.url.params.get("appsecret_proof") != appsecret_proof(self.app_secret, token):
            return self._error(400, "Invalid appsecret_proof", 100)
        if token not in self.tokens:
            return self._error(401, f"Error validating access token {token}", 190)
        if self.graph_error:
            status_code, message, code = self.graph_error
            return self._error(status_code, message.replace("{token}", token), code)

        _, _, path = request.url.path.lstrip("/").partition("/")
        parts = path.split("/")

        if request.method == "POST" and len(parts) == 2 and parts[1] == "messages":
            if self.send_error:
                status_code, message, code = self.send_error
                return self._error(status_code, message.replace("{token}", token), code)
            self.sent.append(json.loads(request.content))
            return httpx.Response(200, json={"messages": [{"id": f"wamid.T{uuid.uuid4().hex}"}]})

        if len(parts) == 2 and parts[1] == "message_templates":
            waba = parts[0]
            if waba not in self.tokens[token]:
                return self._error(400, "Object does not exist", 100)
            items = self.templates.get(waba, [])
            start = int(request.url.params.get("after", "0") or 0)
            page = items[start:start + self.page_size]
            body: dict = {"data": page}
            if start + self.page_size < len(items):
                body["paging"] = {
                    "cursors": {"after": str(start + self.page_size)},
                    "next": "https://graph.facebook.com/next-page-not-followed",
                }
            return httpx.Response(200, json=body)

        if len(parts) == 1 and parts[0] in self.media:
            item = self.media[parts[0]]
            if request.url.params.get("phone_number_id") != item.phone_number_id:
                return self._error(400, "Media does not belong to this phone number", 100)
            return httpx.Response(200, json={
                "messaging_product": "whatsapp",
                "id": parts[0],
                "url": item.url,
                "mime_type": item.mime_type,
                "sha256": item.sha256,
                "file_size": item.file_size,
            })

        return self._error(404, "Unknown path", 100)
