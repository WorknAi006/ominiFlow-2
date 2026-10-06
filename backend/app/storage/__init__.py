from pathlib import Path

from app.core.config import BASE_DIR, settings
from app.storage.base import MediaStorage, StorageError
from app.storage.local import LocalFileStorage

DEFAULT_LOCAL_ROOT = BASE_DIR / "backend" / "var" / "media"


def get_storage() -> MediaStorage:
    """Storage backend from settings. Add S3/R2/MinIO backends here."""

    if settings.media_storage_backend == "local":
        return LocalFileStorage(Path(settings.media_local_root or DEFAULT_LOCAL_ROOT))

    raise StorageError("Media storage backend is not configured.")


__all__ = ["MediaStorage", "StorageError", "get_storage"]
