"""Container readiness: database + Redis; API also checks the real DB endpoint."""
import json
import sys
from urllib.request import urlopen

from sqlalchemy import text
from redis import Redis

from app.core.config import settings
from app.core.database import engine


def main():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    with Redis.from_url(settings.redis_url, socket_timeout=3) as redis:
        if not redis.ping():
            raise RuntimeError("Redis unavailable")
    if sys.argv[1] == "api":
        with urlopen("http://127.0.0.1:8000/health/database", timeout=4) as response:
            if json.load(response).get("status") != "ok":
                raise RuntimeError("API unavailable")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Readiness check failed", file=sys.stderr)
        sys.exit(1)
