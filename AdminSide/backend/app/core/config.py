from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Omniflow"
    app_env: str = "development"

    database_url: str
    redis_url: str

    frontend_url: str = "http://localhost:3000"
    # Comma-separated browser origins. FRONTEND_URL remains the default/fallback
    # for existing deployments that configure a single frontend origin.
    frontend_origins: str = ""

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    invitation_expire_hours: int = 72

    # Comma-separated Fernet keys used to encrypt channel credentials.
    # The first key encrypts; all keys decrypt (allows key rotation).
    channel_credential_keys: str = ""

    # Meta (WhatsApp Cloud API / Graph API)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_api_base_url: str = "https://graph.facebook.com"
    meta_graph_api_version: str = "v23.0"
    meta_http_timeout_seconds: float = 10.0

    # Shared secret for the WhatsApp webhook verification (GET) handshake.
    whatsapp_webhook_verify_token: str = ""

    # Media storage. "local" for development; S3/R2/MinIO backends plug
    # into app/storage. Default local root: backend/var/media (git-ignored).
    media_storage_backend: str = "local"
    media_local_root: str = ""
    media_download_timeout_seconds: float = 30.0
    media_max_download_attempts: int = 3

    automation_max_nodes: int = 50
    automation_max_steps: int = 50
    automation_max_attempts: int = 5
    automation_execution_timeout_seconds: int = 300
    automation_stale_claim_seconds: int = 60
    automation_worker_healthy_seconds: int = 45
    automation_worker_delayed_seconds: int = 120

    @property
    def allowed_frontend_origins(self) -> list[str]:
        configured = self.frontend_origins or self.frontend_url
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
