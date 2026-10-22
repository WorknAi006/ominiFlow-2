import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import engine
from app.api.auth import router as auth_router
from app.api.channels import router as channels_router
from app.api.tenants import router as tenants_router
from app.api.users import router as users_router
from app.api.roles import router as roles_router
from app.api.whatsapp import router as whatsapp_router
from app.api.facebook import router as facebook_router
from app.api.instagram import router as instagram_router
from app.api.meta_oauth import router as meta_oauth_router
from app.api.web_chat import router as web_chat_router
from app.api.contacts import router as contacts_router
from app.api.tags import router as tags_router
from app.api.custom_fields import router as custom_fields_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router
from app.api.templates import router as templates_router
from app.api.realtime import router as realtime_router
from app.api.automations import router as automations_router
from app.api.keywords import router as keywords_router
from app.api.whatsapp_forms import router as whatsapp_forms_router
from app.api.campaigns import router as campaigns_router
from app.api.ai_config import router as ai_config_router
from app.api.knowledge_bases import router as knowledge_bases_router
from app.api.analytics import router as analytics_router
from app.api.ecommerce import router as ecommerce_router
from app.api.flows import router as flows_router
from app.api.routing_config import router as routing_config_router
from app.api.payments import router as payments_router
from app.api.admin import router as admin_router
from app.core.config import settings

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Omniflow API",
    version="1.0.0",
)

# Browser access is limited to explicitly configured frontend origins. The
# frontend authenticates API calls with Bearer tokens, not cross-site cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# The public Web Chat widget is embedded on arbitrary customer websites, so
# its public endpoints (and only those) allow any origin. They carry no
# credentials — the tenant/channel is derived from the public key in the URL
# — so this does not weaken the authenticated APIs above, which keep the
# strict origin allow-list. Added after CORSMiddleware so it runs outermost
# and can answer the cross-origin preflight the strict middleware would
# otherwise reject.
_PUBLIC_WEB_CHAT_PREFIX = "/api/v1/web-chat/"
_PUBLIC_WEB_CHAT_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "600",
}


@app.middleware("http")
async def public_web_chat_cors(request: Request, call_next):
    if not request.url.path.startswith(_PUBLIC_WEB_CHAT_PREFIX):
        return await call_next(request)
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=_PUBLIC_WEB_CHAT_CORS)
    response = await call_next(request)
    for key, value in _PUBLIC_WEB_CHAT_CORS.items():
        response.headers[key] = value
    return response


# =========================
# API ROUTERS
# =========================

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    tenants_router,
    prefix="/api/v1",
)

app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    roles_router,
    prefix="/api/v1",
)

app.include_router(
    channels_router,
    prefix="/api/v1",
)

app.include_router(
    whatsapp_router,
    prefix="/api/v1",
)

app.include_router(
    facebook_router,
    prefix="/api/v1",
)

app.include_router(
    instagram_router,
    prefix="/api/v1",
)

app.include_router(
    meta_oauth_router,
    prefix="/api/v1",
)

app.include_router(
    web_chat_router,
    prefix="/api/v1",
)

app.include_router(
    contacts_router,
    prefix="/api/v1",
)

app.include_router(
    tags_router,
    prefix="/api/v1",
)

app.include_router(
    custom_fields_router,
    prefix="/api/v1",
)

app.include_router(
    conversations_router,
    prefix="/api/v1",
)

app.include_router(
    messages_router,
    prefix="/api/v1",
)

app.include_router(
    templates_router,
    prefix="/api/v1",
)

app.include_router(
    realtime_router,
    prefix="/api/v1",
)

app.include_router(
    automations_router,
    prefix="/api/v1",
)

app.include_router(
    campaigns_router,
    prefix="/api/v1",
)

app.include_router(
    keywords_router,
    prefix="/api/v1",
)

app.include_router(
    whatsapp_forms_router,
    prefix="/api/v1",
)

app.include_router(
    ai_config_router,
    prefix="/api/v1",
    tags=["AI Configuration"],
)

app.include_router(
    knowledge_bases_router,
    prefix="/api/v1",
    tags=["Knowledge Base"],
)

app.include_router(
    analytics_router,
    prefix="/api/v1",
)

app.include_router(
    ecommerce_router,
    prefix="/api/v1",
)

app.include_router(
    flows_router,
    prefix="/api/v1",
)

app.include_router(
    routing_config_router,
    prefix="/api/v1",
)

app.include_router(
    payments_router,
    prefix="/api/v1",
)

app.include_router(
    admin_router,
    prefix="/api/v1",
)

# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "omniflow-api",
    }


# =========================
# DATABASE HEALTH CHECK
# =========================

@app.get("/health/database")
async def database_health():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )
        database_name = result.scalar()

    return {
        "status": "ok",
        "database": database_name,
    }


# =========================
# BACKGROUND WORKERS
# =========================

def _whatsapp_worker_loop():
    import time
    from app.core.database import SessionLocal
    from app.services.whatsapp_event_processor import process_pending_events
    from app.workers import flow_delivery
    while True:
        try:
            with SessionLocal() as db:
                process_pending_events(db, limit=100)
        except Exception:
            pass
        try:
            flow_delivery.run_once(batch_size=50)
        except Exception:
            pass
        time.sleep(2.0)


@app.on_event("startup")
def start_whatsapp_worker():
    import threading
    worker_thread = threading.Thread(target=_whatsapp_worker_loop, daemon=True, name="whatsapp-event-worker")
    worker_thread.start()


@app.on_event("startup")
def ensure_default_platform_super_admin():
    # The development convenience account has public example credentials.
    # Production administrators must be provisioned explicitly.
    if settings.is_production:
        return
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import hash_password
    try:
        with SessionLocal() as db:
            admin_email = "admin@omniflow.io"
            user = db.query(User).filter(User.email == admin_email).first()
            if not user:
                admin_user = User(
                    email=admin_email,
                    password_hash=hash_password("OmniflowAdmin2026!"),
                    first_name="Platform",
                    last_name="Admin",
                    is_active=True,
                    is_verified=True,
                    is_platform_super_admin=True,
                )
                db.add(admin_user)
                db.commit()
                logger.info("Default platform super admin created: %s", admin_email)
            else:
                updated = False
                if not getattr(user, "is_platform_super_admin", False):
                    user.is_platform_super_admin = True
                    updated = True
                if not user.is_active:
                    user.is_active = True
                    updated = True
                if updated:
                    db.commit()
                    logger.info("Platform super admin privileges ensured for: %s", admin_email)
    except Exception as exc:
        logger.warning("Could not auto-seed platform super admin: %s", exc)



