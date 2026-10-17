"""
WebSocket: /api/v1/ws/inbox (realtime inbox: message.created, message.status_changed).

Protocol:
1. Client connects, then sends {"type": "auth", "token": "<access JWT>"}
   within AUTH_TIMEOUT_SECONDS. The token is sent in the first message,
   not the URL, so it never appears in access logs.
2. The token is validated with the existing auth dependencies (JWT, user,
   tenant membership, role) plus the message:read permission. The tenant
   comes only from the verified token + membership.
3. Server subscribes to omniflow:tenant:{tenant_id}:inbox, replies
   {"event": "ready"} and forwards allowlisted inbox events for that tenant.
4. The socket is closed when the access token expires; the client
   reconnects with a fresh token.

Close codes: 4401 unauthenticated/expired, 4403 forbidden,
4408 auth timeout, 1011 realtime unavailable.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import (
    get_current_membership,
    get_current_role,
    get_current_tenant,
    get_current_user,
    get_token_payload,
    has_permission,
)
from app.core.database import get_db
from app.services import realtime_service
from app.services.realtime_service import CLIENT_EVENTS, RealtimeUnavailableError, inbox_channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Realtime"])

AUTH_TIMEOUT_SECONDS = 10.0
REQUIRED_PERMISSION = "message:read"

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_AUTH_TIMEOUT = 4408
CLOSE_UNAVAILABLE = 1011


class _AuthFailed(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def _authenticate(app: Any, token: object) -> tuple[uuid.UUID, int]:
    """
    Reuse the HTTP auth chain. Returns (tenant_id, token exp). Runs in a
    worker thread with a short-lived DB session (not held for the socket).
    """

    if not isinstance(token, str) or not token:
        raise _AuthFailed(CLOSE_UNAUTHENTICATED)

    db_factory = app.dependency_overrides.get(get_db, get_db)
    db_generator = db_factory()
    db = next(db_generator)

    try:
        payload = get_token_payload(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
        user = get_current_user(payload, db)
        tenant = get_current_tenant(payload, user, db)
        role = get_current_role(get_current_membership(user, tenant, db), db)

        if not has_permission(db, role, REQUIRED_PERMISSION):
            raise _AuthFailed(CLOSE_FORBIDDEN)

        return tenant.id, int(payload["exp"])

    except HTTPException as exc:
        raise _AuthFailed(
            CLOSE_UNAUTHENTICATED if exc.status_code == 401 else CLOSE_FORBIDDEN
        ) from None
    finally:
        db_generator.close()


async def _receive_auth(websocket: WebSocket) -> object:
    raw = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_SECONDS)
    try:
        message = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(message, dict) or message.get("type") != "auth":
        return None
    # Only the token is read; any tenant_id/user_id/role sent is ignored.
    return message.get("token")


async def _forward(websocket: WebSocket, subscription: Any, tenant_id: uuid.UUID) -> None:
    async for raw in subscription:
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        # Defense in depth: only this tenant's allowlisted client events.
        if (
            isinstance(event, dict)
            and event.get("event") in CLIENT_EVENTS
            and event.get("tenant_id") == str(tenant_id)
        ):
            await websocket.send_text(json.dumps(event))


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


@router.websocket("/ws/inbox")
async def inbox_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        token = await _receive_auth(websocket)
    except asyncio.TimeoutError:
        await websocket.close(code=CLOSE_AUTH_TIMEOUT)
        return
    except WebSocketDisconnect:
        return

    try:
        tenant_id, expires_at = await run_in_threadpool(_authenticate, websocket.app, token)
    except _AuthFailed as exc:
        await websocket.close(code=exc.code)
        return

    try:
        subscription = await realtime_service.get_broker().subscribe(inbox_channel(tenant_id))
    except RealtimeUnavailableError:
        logger.warning("Realtime subscription unavailable.")
        await websocket.close(code=CLOSE_UNAVAILABLE)
        return

    close_code: int | None = None
    tasks: list[asyncio.Task] = []
    try:
        await websocket.send_json({"event": "ready"})

        forward = asyncio.create_task(_forward(websocket, subscription, tenant_id))
        disconnect = asyncio.create_task(_wait_for_disconnect(websocket))
        tasks = [forward, disconnect]
        remaining = max(expires_at - datetime.now(timezone.utc).timestamp(), 0)

        done, pending = await asyncio.wait(
            tasks, timeout=remaining, return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        if not done:
            close_code = CLOSE_UNAUTHENTICATED  # token expired
        elif forward in done:
            if forward.exception() is not None:
                logger.warning("Realtime stream ended: %s", type(forward.exception()).__name__)
            close_code = CLOSE_UNAVAILABLE

    except WebSocketDisconnect:
        pass
    finally:
        # Also runs if this handler itself is cancelled (e.g. shutdown):
        # never leave the helper tasks running on a dead socket.
        for task in tasks:
            if not task.done():
                task.cancel()
        await subscription.close()

    if close_code is not None:
        try:
            await websocket.close(code=close_code)
        except RuntimeError:
            pass
