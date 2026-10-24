"""Create a production .env once, without printing or replacing secrets."""
import base64
import os
from pathlib import Path
import secrets


def main():
    root = Path(__file__).resolve().parents[1]
    password = secrets.token_hex(32)
    values = {
        "APP_NAME": "Omniflow",
        "APP_ENV": "production",
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": f"postgresql+psycopg://fmfilms:{password}@postgres:5432/fmfilms",
        "REDIS_URL": "redis://redis:6379/0",
        "FRONTEND_URL": "https://fmfilms.in",
        "FRONTEND_ORIGINS": "https://fmfilms.in,https://www.fmfilms.in,https://admin.fmfilms.in",
        "JWT_SECRET": secrets.token_hex(48),
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "10080",
        "INVITATION_EXPIRE_HOURS": "72",
        "PASSWORD_RESET_EXPIRE_MINUTES": "60",
        "SMTP_PORT": "587",
        "SMTP_FROM_EMAIL": "noreply@fmfilms.in",
        "SMTP_FROM_NAME": "Omniflow",
        "CHANNEL_CREDENTIAL_KEYS": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "META_GRAPH_API_VERSION": "v23.0",
        "META_OAUTH_REDIRECT_URI": "https://fmfilms.in/api/v1/channels/oauth/callback",
        "MEDIA_STORAGE_BACKEND": "local",
        "MEDIA_LOCAL_ROOT": "/app/var/media",
        "MEDIA_DOWNLOAD_TIMEOUT_SECONDS": "30",
        "MEDIA_MAX_DOWNLOAD_ATTEMPTS": "3",
        "OPENAI_CHAT_MODEL": "gpt-4o-mini",
        "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
        "AI_CREDITS_PER_1K_TOKENS": "1.0",
        "AI_REPLY_MAX_TOKENS": "500",
        "AI_REPLY_TEMPERATURE": "0.3",
    }
    lines = []
    for line in (root / ".env.example").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0]
            lines.append(f"{key}={values.get(key, '')}")
        else:
            lines.append(line)
    try:
        fd = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Existing .env preserved; nothing changed.")
        return
    with os.fdopen(fd, "w", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("Created private .env. Configure optional SMTP, Meta, AI and payment credentials on the VPS.")


if __name__ == "__main__":
    main()
