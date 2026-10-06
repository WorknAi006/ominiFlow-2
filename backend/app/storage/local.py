import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

from app.storage.base import MediaStorage, StorageError, validate_key


class LocalFileStorage(MediaStorage):
    """
    Development storage on the local filesystem. Every resolved path is
    checked to stay inside the root directory; writes are atomic.
    """

    backend_name = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / validate_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Invalid storage key.")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                os.replace(tmp, path)
            except BaseException:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
        except OSError:
            raise StorageError("Media could not be stored.") from None

    def iter_chunks(self, key: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        path = self._path(key)
        try:
            handle = path.open("rb")
        except OSError:
            raise StorageError("Stored media is not available.") from None

        def generator() -> Iterator[bytes]:
            with handle:
                while chunk := handle.read(chunk_size):
                    yield chunk

        return generator()

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError:
            raise StorageError("Stored media could not be deleted.") from None

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
