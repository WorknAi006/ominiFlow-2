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
from app.api.web_chat import router as web_chat_router
from app.api.contacts import router as contacts_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router
from app.api.templates import router as templates_router
from app.api.realtime import router as realtime_router
from app.api.automations import router as automations_router
from app.core.config import settings


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
    web_chat_router,
    prefix="/api/v1",
)

app.include_router(
    contacts_router,
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
