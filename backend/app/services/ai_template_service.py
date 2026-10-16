"""
Generate WhatsApp message-template drafts with OpenAI.

Returns structured drafts the user can pick and edit. The key is resolved per
tenant (same as AI replies). Returns None when no key is configured.
"""
import json
import logging
import re
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger("app.services.ai_template")


class AiProviderError(Exception):
    """The AI provider was reachable but failed (bad key, no quota, etc.).
    Carries a sanitized, user-safe message."""


def _provider_message(exc: Exception) -> str:
    # OpenAI SDK errors expose the structured body on .body or .response.
    for source in (getattr(exc, "body", None), None):
        data = source
        if data is None:
            resp = getattr(exc, "response", None)
            if resp is not None:
                try:
                    data = resp.json()
                except Exception:  # noqa: BLE001
                    data = None
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            message = data["error"].get("message")
            if message:
                return str(message)[:300]
    message = getattr(exc, "message", None)
    return str(message or exc)[:300]

_VALID_HEADER = {"none", "text", "image", "video", "document"}
_VALID_CATEGORY = {"MARKETING", "UTILITY", "AUTHENTICATION"}

SYSTEM_PROMPT = (
    "You are an expert WhatsApp Business message-template copywriter. "
    "Return ONLY JSON: {\"templates\": [ ... ]}. Each template object has: "
    "name (lowercase letters, digits and underscores only, <=60 chars, unique), "
    "category (one of MARKETING, UTILITY, AUTHENTICATION), "
    "language (BCP-47 like en_US, hi, es), "
    "header_type (one of none, text, image, video, document), "
    "header_text (<=60 chars; only when header_type is text, else null), "
    "body_text (<=1024 chars; use {{1}}, {{2}} for variables), "
    "footer_text (<=60 chars or null), "
    "buttons (array of up to 3 short button labels, <=20 chars each). "
    "WhatsApp templates do NOT support audio headers. For image/video/document "
    "headers, write a body caption and set header_text to null. Make the "
    "templates varied, realistic and compliant (no spammy claims)."
)


def _slug(value: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9_]", "_", str(value or "").lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)[:60]
    return slug or f"ai_template_{index + 1}"


def _normalize(raw: dict, index: int, default_language: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    body = str(raw.get("body_text") or "").strip()
    if not body:
        return None
    header_type = str(raw.get("header_type") or "none").lower()
    if header_type not in _VALID_HEADER:
        header_type = "none"
    category = str(raw.get("category") or "MARKETING").upper()
    if category not in _VALID_CATEGORY:
        category = "MARKETING"
    buttons = [str(b).strip()[:20] for b in (raw.get("buttons") or []) if str(b).strip()][:3]
    header_text = raw.get("header_text")
    header_text = str(header_text).strip()[:60] if (header_type == "text" and header_text) else None
    footer = raw.get("footer_text")
    footer = str(footer).strip()[:60] if footer else None
    return {
        "name": _slug(raw.get("name") or f"ai_template_{index + 1}", index),
        "category": category,
        "language": str(raw.get("language") or default_language)[:20],
        "header_type": header_type,
        "header_text": header_text,
        "body_text": body[:1024],
        "footer_text": footer,
        "buttons": buttons,
    }


def generate_templates(
    db: Session,
    tenant_id: uuid.UUID,
    prompt: str,
    count: int = 10,
    category: str | None = None,
    language: str | None = None,
) -> dict | None:
    """Generate up to `count` template drafts. Returns
    {"drafts", "tokens_in", "tokens_out", "model"} or None if not configured."""
    from app.services.ai_reply_service import _resolve_key_and_model

    key, model = _resolve_key_and_model(db, tenant_id)
    if not key:
        return None

    default_language = language or "en_US"
    user_prompt = (
        f"Generate {count} distinct WhatsApp message templates for this use case:\n{prompt}\n"
        f"Preferred category: {category or 'any appropriate'}. Preferred language: {default_language}."
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.7,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("ai_template_failed", extra={"error_type": type(exc).__name__})
        raise AiProviderError(_provider_message(exc)) from None

    content = resp.choices[0].message.content if resp.choices else None
    if not content:
        raise AiProviderError("The AI returned an empty response. Please try again.")
    try:
        parsed = json.loads(content)
    except ValueError:
        raise AiProviderError("The AI response could not be read. Please try again.")
    raw_list = parsed.get("templates") if isinstance(parsed, dict) else None
    if not isinstance(raw_list, list):
        raw_list = parsed.get("items") if isinstance(parsed, dict) else None
    if not isinstance(raw_list, list):
        raise AiProviderError("The AI did not return any templates. Try rephrasing your description.")

    drafts = []
    for i, raw in enumerate(raw_list[:count]):
        norm = _normalize(raw, i, default_language)
        if norm is not None:
            drafts.append(norm)
    if not drafts:
        raise AiProviderError("The AI did not return any usable templates. Try rephrasing your description.")

    usage = getattr(resp, "usage", None)
    return {
        "drafts": drafts,
        "tokens_in": int(getattr(usage, "prompt_tokens", 0) or 0),
        "tokens_out": int(getattr(usage, "completion_tokens", 0) or 0),
        "model": model,
    }
