"""
Stateful flow execution engine.

A keyword (or any trigger) starts a ``FlowSession`` for a conversation. The
engine walks the flow's nodes from the Start node, sending messages through the
connected channel, and *pauses* when a node needs the customer to reply
(button / list / get-user-data) or a delay to elapse. When the customer sends
the next message, ``resume_with_reply`` advances the flow along the chosen
branch; delays are resumed by the flow-delivery worker.

Supported node types (``data.messageType``):
  text, template, button, list, condition, delay, get_user_data,
  send_email (best-effort/log), actions (tags/fields best-effort).

Interactive buttons/lists are sent as a numbered text menu (the outbound
service supports text + template), and the reply is matched by number or title.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Contact, Conversation, Flow, FlowSession, FlowSessionStatus,
    FlowSessionWait, User,
)
from app.schemas.message import (
    InteractiveButton,
    InteractiveHeader,
    InteractiveListItem,
    InteractiveMessageCreate,
    MediaMessageCreate,
    TemplateMessageCreate,
    TextMessageCreate,
)
from app.services import contact_service, outbound_message_service
from app.services.outbound_message_service import OutboundMessageError

logger = logging.getLogger("app.services.flow_engine")

_NS = uuid.UUID("9a7e4c1b-2d3f-4a56-8b90-1c2d3e4f5a6b")
_MAX_STEPS = 100


# --------------------------------------------------------------------------
# Graph helpers
# --------------------------------------------------------------------------

def _node_map(session: FlowSession) -> dict[str, dict[str, Any]]:
    return {str(n.get("id")): n for n in (session.nodes or [])}


def _start_node(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    start = next((n for n in nodes if (n.get("data") or {}).get("isStart")), None)
    if start is None and nodes:
        start = nodes[0]
    return start


def _clean_opt_id(opt: dict[str, Any], i: int) -> str:
    raw_id = str(opt.get("id") or "").strip()
    if not raw_id:
        return str(i)
    if raw_id.startswith(("btn:", "item:")):
        return raw_id.split(":", 1)[1]
    return raw_id


def _next_node_id(session: FlowSession, node_id: str, handle: str | None) -> str | None:
    edges = [e for e in (session.edges or []) if str(e.get("source")) == node_id]
    if handle is not None:
        h_norm = str(handle).strip()
        h_core = h_norm.split(":", 1)[1] if ":" in h_norm else h_norm
        # Pass 1: exact handle match (e.g. "item:f347be39" == "item:f347be39")
        for e in edges:
            sh = str(e.get("sourceHandle") or "").strip()
            if sh == h_norm:
                return str(e.get("target"))
        # Pass 2: core ID match ignoring prefix (e.g. "f347be39" == "item:f347be39" or "btn:1" == "1")
        for e in edges:
            sh = str(e.get("sourceHandle") or "").strip()
            sh_core = sh.split(":", 1)[1] if ":" in sh else sh
            if sh_core and (sh_core == h_core or sh_core == h_norm or sh == h_core):
                return str(e.get("target"))
        # Fall back to a default/continue edge when the branch is unwired.
    for e in edges:
        if e.get("sourceHandle") in (None, "", "continue"):
            return str(e.get("target"))
    return str(edges[0].get("target")) if edges else None


def _mt(node: dict[str, Any]) -> str:
    return str((node.get("data") or {}).get("messageType") or "text")


# --------------------------------------------------------------------------
# Text / variables
# --------------------------------------------------------------------------

def _interpolate(textval: str, contact: Contact | None, variables: dict[str, Any]) -> str:
    if not textval:
        return textval
    name = (contact_service.contact_name(contact) if contact else "") or ""
    phone = (contact.normalized_phone_number if contact else "") or ""
    out = (textval
           .replace("{{contact_name}}", name)
           .replace("{{contact_phone}}", phone)
           .replace("{{user_last_input}}", str(variables.get("user_last_input", ""))))
    for key, val in (variables or {}).items():
        out = out.replace("{{" + str(key) + "}}", str(val))
    return out


def _options(node: dict[str, Any]) -> list[dict[str, Any]]:
    data = node.get("data") or {}
    if _mt(node) == "list":
        return list(data.get("listItems") or [])
    return list(data.get("buttons") or [])


def _option_prefix(node: dict[str, Any]) -> str:
    return "item" if _mt(node) == "list" else "btn"


def _menu_text(node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> str:
    data = node.get("data") or {}
    body = _interpolate(str(data.get("message") or "").strip(), contact, variables)
    lines = [body] if body else []
    for i, opt in enumerate(_options(node), start=1):
        title = str(opt.get("title") or opt.get("label") or f"Option {i}").strip()
        lines.append(f"{i}. {title}")
    if not lines:
        lines = ["Please choose an option."]
    return "\n".join(lines)


def _match_choice(node: dict[str, Any], reply: str, reply_id: str | None = None, reply_title: str | None = None) -> str | None:
    options = _options(node)
    if not options:
        return None
    prefix = _option_prefix(node)

    # 0. Provider-verified exact interactive reply ID
    if reply_id:
        rid = reply_id.strip().lower()
        rid_core = rid.split(":", 1)[1] if ":" in rid else rid
        for i, opt in enumerate(options):
            cid = _clean_opt_id(opt, i).lower()
            raw_opt_id = str(opt.get("id") or "").strip().lower()
            if rid == cid or rid_core == cid or rid == raw_opt_id:
                return f"{prefix}:{_clean_opt_id(opt, i)}"

    # 1. Provider-verified exact interactive reply title
    if reply_title:
        rt = reply_title.strip().lower()
        for i, opt in enumerate(options):
            title = str(opt.get("title") or opt.get("label") or "").strip().lower()
            if rt == title:
                return f"{prefix}:{_clean_opt_id(opt, i)}"

    r = reply.strip().lower()
    r_core = r.split(":", 1)[1] if ":" in r else r

    # 2. By number (e.g. "1", "2").
    if r.isdigit():
        idx = int(r) - 1
        if 0 <= idx < len(options):
            return f"{prefix}:{_clean_opt_id(options[idx], idx)}"

    # 3. By ID match directly.
    for i, opt in enumerate(options):
        cid = _clean_opt_id(opt, i).lower()
        raw_opt_id = str(opt.get("id") or "").strip().lower()
        if r == cid or r_core == cid or r == raw_opt_id:
            return f"{prefix}:{_clean_opt_id(opt, i)}"

    # 4. By EXACT title match.
    for i, opt in enumerate(options):
        title = str(opt.get("title") or opt.get("label") or "").strip().lower()
        if title and r == title:
            return f"{prefix}:{_clean_opt_id(opt, i)}"

    # 5. By partial substring match fallback.
    for i, opt in enumerate(options):
        title = str(opt.get("title") or opt.get("label") or "").strip().lower()
        if title and (r in title or title in r):
            return f"{prefix}:{_clean_opt_id(opt, i)}"

    return None


# --------------------------------------------------------------------------
# Sending
# --------------------------------------------------------------------------

def _actor(db: Session, session: FlowSession) -> User | None:
    if session.actor_user_id:
        return db.get(User, session.actor_user_id)
    return None


def _send_text(db: Session, session: FlowSession, node_id: str, text: str, seq: str = "") -> None:
    actor = _actor(db, session)
    if actor is None:
        raise OutboundMessageError("No user to send as.")
    key = uuid.uuid5(_NS, f"flow:{session.id}:{node_id}:{seq}")
    outbound_message_service.send_message(
        db, session.tenant_id, actor, session.conversation_id,
        TextMessageCreate(type="text", text=text[:4096]), idempotency_key=key,
    )


def _send_template(db: Session, session: FlowSession, node: dict[str, Any]) -> None:
    data = node.get("data") or {}
    actor = _actor(db, session)
    if actor is None:
        raise OutboundMessageError("No user to send as.")
    key = uuid.uuid5(_NS, f"flow:{session.id}:{node.get('id')}:template")
    outbound_message_service.send_message(
        db, session.tenant_id, actor, session.conversation_id,
        TemplateMessageCreate(
            type="template",
            template_name=str(data.get("templateName") or data.get("template_name") or ""),
            language=str(data.get("templateLanguage") or data.get("language") or "en_US"),
            components=data.get("templateParams") or data.get("components") or [],
        ),
        idempotency_key=key,
    )


# --------------------------------------------------------------------------
# Interactive (buttons + header/footer) and media
# --------------------------------------------------------------------------

_ASSET_URL_PREFIX = "/api/flows/assets/"


def _asset_key(data: dict[str, Any], url_field: str = "mediaUrl", key_field: str = "mediaKey") -> str | None:
    """Return the storage key for a flow asset from its stored key or URL."""
    key = data.get(key_field)
    if key:
        return str(key)
    url = data.get(url_field)
    if url and str(url).startswith(_ASSET_URL_PREFIX):
        return str(url)[len(_ASSET_URL_PREFIX):]
    return None


def _build_header(data: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> InteractiveHeader | None:
    header = data.get("header")
    if not isinstance(header, dict):
        return None
    htype = str(header.get("type") or "none")
    if htype in ("", "none"):
        return None
    if htype == "text":
        text = _interpolate(str(header.get("text") or "").strip(), contact, variables)
        return InteractiveHeader(type="text", text=text[:60]) if text else None
    if htype in ("image", "video", "document"):
        key = _asset_key(header)
        url = str(header.get("mediaUrl") or "").strip() if not key else None
        if not key and (not url or not url.startswith(("http://", "https://"))):
            return None
        name = header.get("mediaName")
        return InteractiveHeader(
            type=htype,
            media_key=key,
            media_url=url,
            filename=(str(name)[:255] if name else None),
        )
    return None


def _build_buttons(data: dict[str, Any]) -> list[InteractiveButton]:
    out: list[InteractiveButton] = []
    for i, b in enumerate(data.get("buttons") or []):
        if not isinstance(b, dict):
            continue
        title = str(b.get("title") or "").strip()
        if not title:
            continue
        kind = str(b.get("kind") or "reply")
        if kind not in ("reply", "url", "call"):
            kind = "reply"
        url = b.get("url")
        phone = b.get("phoneNumber") or b.get("phone_number")
        out.append(InteractiveButton(
            id=str(b.get("id") or f"btn{i}")[:256],
            title=title[:20],
            kind=kind,
            url=(str(url)[:2000] if kind == "url" and url else None),
            phone_number=(str(phone)[:32] if kind == "call" and phone else None),
        ))
    return out


def _wrap_header_footer(text: str, data: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> str:
    """Compose a text header (as a bold first line) and footer around a body,
    for non-interactive messages (text / media caption / list / prompt).
    WhatsApp only renders native header/footer on interactive messages."""
    parts: list[str] = []
    header = data.get("header")
    if isinstance(header, dict) and str(header.get("type")) == "text":
        htext = _interpolate(str(header.get("text") or "").strip(), contact, variables)
        if htext:
            parts.append(f"*{htext}*")
    if text:
        parts.append(text)
    footer = _interpolate(str(data.get("footer") or "").strip(), contact, variables)
    if footer:
        parts.append(footer)
    return "\n\n".join(parts)


def _has_reply_button(data: dict[str, Any]) -> bool:
    return any(
        isinstance(b, dict)
        and str(b.get("kind") or "reply") == "reply"
        and str(b.get("title") or "").strip()
        for b in (data.get("buttons") or [])
    )


def _send_interactive(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    data = node.get("data") or {}
    actor = _actor(db, session)
    if actor is None:
        raise OutboundMessageError("No user to send as.")
    body = _interpolate(str(data.get("message") or "").strip(), contact, variables) or "Please choose an option."
    footer = _interpolate(str(data.get("footer") or "").strip(), contact, variables) or None
    key = uuid.uuid5(_NS, f"flow:{session.id}:{node.get('id')}:interactive")
    try:
        outbound_message_service.send_message(
            db, session.tenant_id, actor, session.conversation_id,
            InteractiveMessageCreate(
                type="interactive",
                body=body[:1024],
                header=_build_header(data, contact, variables),
                footer=(footer[:60] if footer else None),
                buttons=_build_buttons(data),
            ),
            idempotency_key=key,
        )
    except OutboundMessageError:
        # Fall back to clear formatted text menu if provider rejects interactive payload
        menu = _wrap_header_footer(_menu_text(node, contact, variables), data, contact, variables)
        _send_text(db, session, str(node["id"]), menu, seq="fallback_btn_menu")


def _send_interactive_list(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    data = node.get("data") or {}
    actor = _actor(db, session)
    if actor is None:
        raise OutboundMessageError("No user to send as.")
    body = _interpolate(str(data.get("message") or "").strip(), contact, variables) or "Please choose an option."
    footer = _interpolate(str(data.get("footer") or "").strip(), contact, variables) or None
    raw_items = data.get("listItems") or []
    items: list[InteractiveListItem] = []
    for i, it in enumerate(raw_items[:10]):
        if isinstance(it, dict):
            item_id = str(it.get("id") or f"opt_{i}")[:200]
            item_title = str(it.get("title") or f"Option {i+1}")[:24]
            item_desc = str(it.get("description") or "")[:72] if it.get("description") else None
            items.append(InteractiveListItem(id=item_id, title=item_title, description=item_desc))

    if not items:
        text = _wrap_header_footer(body, data, contact, variables)
        _send_text(db, session, str(node["id"]), text)
        return

    btn_text = str(data.get("buttonText") or "Select Option")[:20]
    header = _build_header(data, contact, variables)
    if header and header.type != "text":
        header = None

    key = uuid.uuid5(_NS, f"flow:{session.id}:{node.get('id')}:list")
    try:
        outbound_message_service.send_message(
            db, session.tenant_id, actor, session.conversation_id,
            InteractiveMessageCreate(
                type="interactive",
                interactive_type="list",
                button_text=btn_text,
                body=body[:1024],
                header=header,
                footer=(footer[:60] if footer else None),
                list_items=items,
            ),
            idempotency_key=key,
        )
    except OutboundMessageError:
        menu = _wrap_header_footer(_menu_text(node, contact, variables), data, contact, variables)
        _send_text(db, session, str(node["id"]), menu, seq="fallback_menu")


def _send_media(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> bool:
    """Send the node's uploaded media or external media URL. Returns False when
    no media is configured so the caller can fall back to sending caption text."""
    data = node.get("data") or {}
    media_key = _asset_key(data)
    media_url = str(data.get("mediaUrl") or "").strip() if not media_key else None
    if media_url and not media_url.startswith(("http://", "https://")):
        media_url = None
    if not media_key and not media_url:
        return False
    actor = _actor(db, session)
    if actor is None:
        raise OutboundMessageError("No user to send as.")
    caption = _wrap_header_footer(_interpolate(str(data.get("message") or "").strip(), contact, variables), data, contact, variables) or None
    name = data.get("mediaName")
    key = uuid.uuid5(_NS, f"flow:{session.id}:{node.get('id')}:media")
    outbound_message_service.send_message(
        db, session.tenant_id, actor, session.conversation_id,
        MediaMessageCreate(
            type="media",
            media_type=_mt(node),
            media_key=media_key,
            media_url=media_url,
            caption=(caption[:1024] if caption else None),
            filename=(str(name)[:255] if name else None),
        ),
        idempotency_key=key,
    )
    return True


# --------------------------------------------------------------------------
# Condition evaluation
# --------------------------------------------------------------------------

def _condition_source_value(node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> str:
    cond = (node.get("data") or {}).get("condition") or {}
    source = str(cond.get("source") or "last_input")
    if source == "last_input":
        return str(variables.get("user_last_input", ""))
    if source.startswith("variable:"):
        return str(variables.get(source.split(":", 1)[1], ""))
    if source == "contact_name":
        return (contact_service.contact_name(contact) if contact else "") or ""
    if source == "contact_phone":
        return (contact.normalized_phone_number if contact else "") or ""
    return str(variables.get(source, ""))


def _eval_condition(node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> bool:
    cond = (node.get("data") or {}).get("condition") or {}
    op = str(cond.get("operator") or "is")
    target = str(cond.get("value") or "").strip().lower()
    value = _condition_source_value(node, contact, variables).strip().lower()
    if op == "is":
        return value == target
    if op == "is_not":
        return value != target
    if op == "contains":
        return target in value
    if op == "doesnt_contain":
        return target not in value
    if op == "starts_with":
        return value.startswith(target)
    if op == "ends_with":
        return value.endswith(target)
    if op == "has_value":
        return value != ""
    if op == "has_no_value":
        return value == ""
    return False


# --------------------------------------------------------------------------
# Node execution — returns (kind, payload)
#   ("continue", None) | ("branch", handle) | ("wait_reply", None)
#   | ("wait_delay", seconds) | ("end", None) | ("fail", detail)
# --------------------------------------------------------------------------

def _execute(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None) -> tuple[str, Any]:
    mt = _mt(node)
    data = node.get("data") or {}
    variables = dict(session.variables or {})
    try:
        if mt == "text":
            body = _interpolate(str(data.get("message") or "").strip(), contact, variables)
            text = _wrap_header_footer(body, data, contact, variables)
            if text:
                _send_text(db, session, str(node["id"]), text)
            return ("continue", None)

        if mt in ("audio", "document", "image", "video"):
            # Send the uploaded media as a real WhatsApp media message; fall
            # back to the caption as text when no file is attached.
            if not _send_media(db, session, node, contact, variables):
                text = _interpolate(str(data.get("message") or "").strip(), contact, variables)
                if text:
                    _send_text(db, session, str(node["id"]), text)
            return ("continue", None)

        if mt == "template":
            _send_template(db, session, node)
            return ("continue", None)

        if mt == "button":
            # Real interactive message (header/body/footer + typed buttons).
            # Only pause for a reply when there are quick-reply buttons to
            # branch on; URL/call-only messages just continue.
            _send_interactive(db, session, node, contact, variables)
            return ("wait_reply", None) if _has_reply_button(data) else ("continue", None)

        if mt == "list":
            _send_interactive_list(db, session, node, contact, variables)
            return ("wait_reply", None)

        if mt == "get_user_data":
            prompt = _interpolate(str(data.get("message") or "Please reply.").strip(), contact, variables)
            _send_text(db, session, str(node["id"]), _wrap_header_footer(prompt, data, contact, variables))
            return ("wait_reply", None)

        if mt == "condition":
            return ("branch", "true" if _eval_condition(node, contact, variables) else "false")

        if mt == "delay":
            seconds = _delay_seconds(data)
            return ("wait_delay", seconds)

        if mt == "send_email":
            to_addr = _interpolate(str(data.get("emailTo") or "").strip(), contact, variables)
            subject = _interpolate(str(data.get("emailSubject") or "Message from WhatsApp").strip(), contact, variables)
            logger.info("flow_send_email", extra={"session_id": str(session.id), "to": to_addr, "subject": subject})
            return ("continue", None)

        if mt == "external_api":
            _execute_external_api(session, node, contact, variables)
            return ("continue", None)

        if mt == "actions":
            _run_actions(db, session, data.get("actions") or [], contact)
            return ("continue", None)

        if mt == "razorpay":
            _execute_razorpay(db, session, node, contact, variables)
            return ("continue", None)

        if mt == "whatsapp_form":
            _execute_whatsapp_form(db, session, node, contact, variables)
            return ("continue", None)

        if mt == "zoho_crm":
            _execute_zoho_crm(session, node, contact, variables)
            return ("continue", None)

        if mt == "carousel":
            _send_template(db, session, node)
            return ("continue", None)

        # Unknown type: skip.
        return ("continue", None)
    except OutboundMessageError as exc:
        return ("fail", f"{type(exc).__name__}: {exc}"[:500])


def _delay_seconds(data: dict[str, Any]) -> int:
    if "delaySeconds" in data:
        try:
            return max(1, min(86400, int(data["delaySeconds"])))
        except (TypeError, ValueError):
            return 60
    value = data.get("delayValue", 1)
    unit = str(data.get("delayUnit", "minutes"))
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 1
    mult = {"seconds": 1, "minutes": 60, "hours": 3600}.get(unit, 60)
    return max(1, min(86400, value * mult))


def _execute_external_api(session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    """Execute a configured HTTP webhook/API call, saving JSON/text response to variables."""
    data = node.get("data") or {}
    url = _interpolate(str(data.get("apiUrl") or data.get("url") or "").strip(), contact, variables)
    if not url or not url.startswith(("http://", "https://")):
        logger.warning("flow_external_api_invalid_url", extra={"session_id": str(session.id), "url": url})
        return
    method = str(data.get("apiMethod") or data.get("method") or "GET").upper()
    headers_raw = data.get("apiHeaders") or data.get("headers") or {}
    body_raw = data.get("apiBody") or data.get("body")
    var_name = str(data.get("responseVariable") or data.get("variable") or "").strip()

    req_headers: dict[str, str] = {}
    if isinstance(headers_raw, dict):
        for k, v in headers_raw.items():
            req_headers[str(k)] = _interpolate(str(v), contact, variables)
    elif isinstance(headers_raw, str) and headers_raw.strip():
        try:
            parsed = json.loads(headers_raw)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    req_headers[str(k)] = _interpolate(str(v), contact, variables)
        except Exception:
            pass

    req_body = None
    if method in ("POST", "PUT", "PATCH") and body_raw is not None:
        if isinstance(body_raw, str):
            req_body = _interpolate(body_raw, contact, variables)
        else:
            req_body = json.dumps(body_raw)
        if "Content-Type" not in req_headers and "content-type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

    import httpx
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.request(
                method=method,
                url=url,
                headers=req_headers if req_headers else None,
                content=req_body.encode("utf-8") if req_body else None,
            )
            resp_text = resp.text[:4096]
            if var_name:
                try:
                    resp_json = resp.json()
                    variables[var_name] = resp_json
                    if isinstance(resp_json, dict):
                        for k, v in resp_json.items():
                            variables[f"{var_name}_{k}"] = str(v)
                except Exception:
                    variables[var_name] = resp_text
                session.variables = variables
    except Exception as exc:
        logger.error("flow_external_api_failed", extra={"session_id": str(session.id), "url": url, "error": str(exc)})
        if var_name:
            variables[f"{var_name}_error"] = str(exc)[:255]
            session.variables = variables


def _run_actions(db: Session, session: FlowSession, actions: list[dict[str, Any]], contact: Contact | None) -> None:
    """Best-effort tag/field actions, reusing the automation action executors."""
    if not actions or contact is None:
        return
    from app.services import automation_service
    conversation = db.get(Conversation, session.conversation_id)
    for action in actions:
        try:
            automation_service._execute_action(db, session.tenant_id, action, contact, conversation)
        except Exception as exc:
            logger.error("flow_action_failed", extra={"session_id": str(session.id), "error_type": type(exc).__name__})


def _execute_razorpay(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    data = node.get("data") or {}
    amount = data.get("amount") or 100
    currency = str(data.get("currency") or "INR").upper()
    desc = _interpolate(str(data.get("description") or data.get("message") or "Order Payment").strip(), contact, variables)
    pay_url = _interpolate(str(data.get("paymentUrl") or "").strip(), contact, variables)
    lines = [
        f"💳 *Payment Request*",
        f"Description: {desc}",
        f"Amount: {currency} {amount}",
    ]
    if pay_url:
        lines.append(f"🔗 Link: {pay_url}")
    text = "\n".join(lines)
    _send_text(db, session, str(node.get("id")), text)


def _execute_whatsapp_form(db: Session, session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    data = node.get("data") or {}
    title = str(data.get("formTitle") or "Open Form")
    msg = _interpolate(str(data.get("message") or "Please fill out the form below:").strip(), contact, variables)
    text = f"{msg}\n\n📋 *{title}*"
    _send_text(db, session, str(node.get("id")), text)


def _execute_zoho_crm(session: FlowSession, node: dict[str, Any], contact: Contact | None, variables: dict[str, Any]) -> None:
    data = node.get("data") or {}
    lead_name = _interpolate(str(data.get("leadName") or "{{contact_name}}"), contact, variables)
    lead_phone = _interpolate(str(data.get("leadPhone") or "{{contact_phone}}"), contact, variables)
    lead_email = _interpolate(str(data.get("leadEmail") or variables.get("user_email", "")), contact, variables)
    variables["zoho_lead_name"] = lead_name
    variables["zoho_lead_phone"] = lead_phone
    variables["zoho_lead_email"] = lead_email
    variables["zoho_status"] = "synced"
    session.variables = variables
    logger.info("flow_zoho_crm_lead", extra={"session_id": str(session.id), "lead": lead_name, "phone": lead_phone})


# --------------------------------------------------------------------------
# Walking / lifecycle
# --------------------------------------------------------------------------

def _run(db: Session, session: FlowSession) -> None:
    contact = db.get(Contact, session.contact_id)
    nodes = _node_map(session)
    node_id = session.current_node_id
    steps = 0
    while node_id and steps < _MAX_STEPS:
        steps += 1
        node = nodes.get(node_id)
        if node is None:
            break
        session.current_node_id = node_id
        kind, payload = _execute(db, session, node, contact)
        if kind == "wait_reply":
            session.status = FlowSessionStatus.WAITING.value
            session.waiting_node_id = node_id
            session.wait_kind = FlowSessionWait.REPLY.value
            db.commit()
            return
        if kind == "wait_delay":
            session.status = FlowSessionStatus.WAITING.value
            session.waiting_node_id = node_id
            session.wait_kind = FlowSessionWait.DELAY.value
            session.resume_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload))
            db.commit()
            return
        if kind == "fail":
            session.status = FlowSessionStatus.FAILED.value
            session.detail = str(payload)
            db.commit()
            return
        if kind == "branch":
            node_id = _next_node_id(session, node_id, str(payload))
        elif kind == "end":
            node_id = None
        else:  # continue
            node_id = _next_node_id(session, node_id, None)
    session.status = FlowSessionStatus.COMPLETED.value
    session.waiting_node_id = None
    session.wait_kind = None
    db.commit()


def active_session_for(db: Session, tenant_id: uuid.UUID, conversation_id: uuid.UUID) -> FlowSession | None:
    return db.execute(
        select(FlowSession).where(
            FlowSession.tenant_id == tenant_id,
            FlowSession.conversation_id == conversation_id,
            FlowSession.status.in_([FlowSessionStatus.ACTIVE.value, FlowSessionStatus.WAITING.value]),
        )
    ).scalar_one_or_none()


def start_session(db: Session, flow: Flow, conversation: Conversation, contact: Contact, actor_user_id: uuid.UUID | None) -> FlowSession | None:
    """Begin a flow for a conversation and run until it waits or ends."""
    if active_session_for(db, flow.tenant_id, conversation.id) is not None:
        return None  # one live flow per conversation
    start = _start_node(flow.nodes or [])
    if start is None:
        return None
    session = FlowSession(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        contact_id=contact.id,
        actor_user_id=actor_user_id,
        nodes=list(flow.nodes or []),
        edges=list(flow.edges or []),
        variables={},
        status=FlowSessionStatus.ACTIVE.value,
        current_node_id=str(start["id"]),
    )
    db.add(session)
    db.flush()
    _run(db, session)
    return session


def resume_with_reply(db: Session, session: FlowSession, reply_text: str) -> None:
    """Advance a WAITING session using the customer's reply."""
    if session.status != FlowSessionStatus.WAITING.value or session.wait_kind != FlowSessionWait.REPLY.value:
        return
    nodes = _node_map(session)
    node = nodes.get(session.waiting_node_id or "")
    if node is None:
        session.status = FlowSessionStatus.FAILED.value
        session.detail = "Waiting node is missing from the flow."
        db.commit()
        return

    reply_id = None
    reply_title = None
    actual_text = reply_text
    if reply_text and reply_text.startswith("{") and reply_text.endswith("}"):
        try:
            payload = json.loads(reply_text)
            if isinstance(payload, dict):
                reply_id = payload.get("id")
                reply_title = payload.get("title")
                actual_text = payload.get("text") or reply_title or reply_id or ""
        except Exception:
            pass

    variables = dict(session.variables or {})
    variables["user_last_input"] = actual_text
    session.variables = variables
    contact = db.get(Contact, session.contact_id)
    mt = _mt(node)

    if mt in ("button", "list"):
        handle = _match_choice(node, actual_text, reply_id=reply_id, reply_title=reply_title)
        if handle is None:
            # Check if this input matches an active keyword to interrupt or restart
            from app.services import keyword_trigger_service
            kw = keyword_trigger_service.find_matching_keyword(db, session.tenant_id, actual_text)
            if kw is not None and (kw.flow_id is not None or (kw.reply_text and kw.reply_text.strip())):
                # Complete the stuck session so the keyword trigger can execute cleanly
                session.status = FlowSessionStatus.COMPLETED.value
                session.waiting_node_id = None
                session.wait_kind = None
                session.detail = f"Interrupted by keyword: {kw.keyword_text}"
                db.commit()
                # Directly run the newly matched flow or reply text
                if kw.flow_id:
                    flow = db.get(Flow, kw.flow_id)
                    conv = db.get(Conversation, session.conversation_id)
                    if flow and conv and contact:
                        start_session(db, flow, conv, contact, session.actor_user_id)
                elif kw.reply_text:
                    _send_text(db, session, str(node["id"]), kw.reply_text.strip(), seq="kw_reply")
                return

            # Unrecognised choice: re-send the menu and keep waiting.
            try:
                _send_text(db, session, str(node["id"]), _menu_text(node, contact, variables), seq="reprompt")
            except OutboundMessageError:
                pass
            db.commit()
            return
        next_id = _next_node_id(session, str(node["id"]), handle)
    elif mt == "get_user_data":
        var = str((node.get("data") or {}).get("variable") or "input")
        variables[var] = actual_text
        session.variables = variables
        next_id = _next_node_id(session, str(node["id"]), None)
    else:
        next_id = _next_node_id(session, str(node["id"]), None)

    session.status = FlowSessionStatus.ACTIVE.value
    session.waiting_node_id = None
    session.wait_kind = None
    session.current_node_id = next_id
    db.flush()
    if next_id is None:
        session.status = FlowSessionStatus.COMPLETED.value
        db.commit()
        return
    _run(db, session)


def capture_reply(db: Session, session: FlowSession, reply_text: str, metadata: dict[str, Any] | None = None) -> None:
    """Store a customer reply on a WAITING(reply) session inside the inbound
    transaction. The worker resumes the flow with it (no sending here)."""
    ir = metadata.get("interactive_reply") if isinstance(metadata, dict) else None
    if ir and isinstance(ir, dict):
        payload = {"text": reply_text, "id": ir.get("id"), "title": ir.get("title")}
        session.pending_reply = json.dumps(payload)[:4096]
    else:
        session.pending_reply = (reply_text or "")[:4096]
    session.pending_reply_at = datetime.now(timezone.utc)
    db.flush()


def resume_pending_replies(db: Session, limit: int = 50) -> dict[str, int]:
    """Resume sessions that captured a reply in the inbound transaction."""
    rows = db.execute(
        select(FlowSession).where(
            FlowSession.status == FlowSessionStatus.WAITING.value,
            FlowSession.wait_kind == FlowSessionWait.REPLY.value,
            FlowSession.pending_reply.isnot(None),
        ).order_by(FlowSession.pending_reply_at.asc()).limit(limit).with_for_update(skip_locked=True)
    ).scalars().all()
    resumed = 0
    for session in rows:
        reply = session.pending_reply or ""
        session.pending_reply = None
        session.pending_reply_at = None
        db.flush()
        try:
            resume_with_reply(db, session, reply)
            resumed += 1
        except Exception as exc:
            db.rollback()
            logger.error("flow_reply_resume_failed", extra={"session_id": str(session.id), "error_type": type(exc).__name__})
    return {"resumed": resumed, "scanned": len(rows)}


def resume_due_delays(db: Session, limit: int = 50) -> dict[str, int]:
    """Continue sessions whose delay has elapsed (called by the worker)."""
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(FlowSession).where(
            FlowSession.status == FlowSessionStatus.WAITING.value,
            FlowSession.wait_kind == FlowSessionWait.DELAY.value,
            FlowSession.resume_at.isnot(None),
            FlowSession.resume_at <= now,
        ).order_by(FlowSession.resume_at.asc()).limit(limit).with_for_update(skip_locked=True)
    ).scalars().all()
    resumed = 0
    for session in rows:
        try:
            node_id = session.waiting_node_id
            session.status = FlowSessionStatus.ACTIVE.value
            session.wait_kind = None
            session.resume_at = None
            session.waiting_node_id = None
            session.current_node_id = _next_node_id(session, str(node_id), None)
            db.flush()
            _run(db, session)
            resumed += 1
        except Exception as exc:
            db.rollback()
            logger.error("flow_delay_resume_failed", extra={"session_id": str(session.id), "error_type": type(exc).__name__})
    return {"resumed": resumed, "scanned": len(rows)}
