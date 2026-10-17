"""
Generate an AI reply to a customer message using OpenAI.

The API key is resolved per tenant: a tenant's own key (tenant_ai_configs,
provider "openai") takes precedence, otherwise the platform key from settings.
When no key is configured the service is a safe no-op (returns None), so AI
replies simply do not fire rather than erroring.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger("app.services.ai_reply")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful customer support assistant replying on WhatsApp. "
    "Answer clearly and concisely (a few short sentences). If you are unsure, "
    "ask a brief clarifying question."
)


def _resolve_key_and_model(db: Session, tenant_id: uuid.UUID) -> tuple[str | None, str]:
    model = settings.openai_chat_model
    try:
        from app.models.tenant_ai_config import TenantAiConfig
        from app.services.credential_service import (
            CredentialEncryptionError,
            get_credential_service,
        )

        cfg = db.scalar(select(TenantAiConfig).where(TenantAiConfig.tenant_id == tenant_id))
        if cfg is not None and getattr(cfg, "provider", None) == "openai" and cfg.api_key_encrypted:
            try:
                key = get_credential_service().decrypt(cfg.api_key_encrypted)
                return key, (cfg.model or model)
            except CredentialEncryptionError:
                pass
    except Exception:  # noqa: BLE001 - never let config lookup break the reply path
        pass
    return (settings.openai_api_key or None), model


def generate_reply(
    db: Session,
    tenant_id: uuid.UUID,
    user_text: str,
    *,
    system_prompt: str | None = None,
) -> dict | None:
    """
    Produce an AI reply. Returns {"text", "tokens_in", "tokens_out", "model"}
    or None when AI is not configured, the input is empty, or the call fails.
    """
    text = (user_text or "").strip()
    if not text:
        return None
    key, model = _resolve_key_and_model(db, tenant_id)
    if not key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": text[:4000]},
            ],
            max_tokens=settings.ai_reply_max_tokens,
            temperature=settings.ai_reply_temperature,
        )
    except Exception as exc:  # noqa: BLE001 - a provider fault must not break delivery
        logger.error("ai_reply_failed", extra={"error_type": type(exc).__name__})
        return None

    choice = resp.choices[0].message.content if resp.choices else None
    if not choice or not choice.strip():
        return None
    usage = getattr(resp, "usage", None)
    return {
        "text": choice.strip(),
        "tokens_in": int(getattr(usage, "prompt_tokens", 0) or 0),
        "tokens_out": int(getattr(usage, "completion_tokens", 0) or 0),
        "model": model,
    }
