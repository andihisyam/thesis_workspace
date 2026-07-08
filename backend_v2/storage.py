import shutil
from pathlib import Path

from backend_v2.config import settings


class LocalStorageAdapter:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, key: str) -> Path:
        candidate = (self.root / key.replace("\\", "/")).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Storage key tidak valid.")
        return candidate

    def write_bytes(self, key: str, content: bytes) -> Path:
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def write_text(self, key: str, content: str) -> Path:
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_bytes(self, key: str) -> bytes:
        return self.resolve(key).read_bytes()

    def read_text(self, key: str) -> str:
        return self.resolve(key).read_text(encoding="utf-8")

    def delete_file(self, key: str) -> None:
        target = self.resolve(key)
        if target.exists() and target.is_file():
            target.unlink()

    def delete_tree(self, key: str) -> None:
        target = self.resolve(key)
        if target.exists() and target != self.root:
            shutil.rmtree(target)


storage = LocalStorageAdapter()
