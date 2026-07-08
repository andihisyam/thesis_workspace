import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or fallback


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(REPOSITORY_ROOT / 'data' / 'v2.db').as_posix()}",
    )
    storage_root: Path = Path(
        os.getenv("V2_STORAGE_ROOT", str(REPOSITORY_ROOT / "data" / "v2_storage"))
    ).resolve()
    cors_origins: tuple[str, ...] = _csv_env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    session_cookie_name: str = "thesis_session"
    session_cookie_domain: str | None = os.getenv("SESSION_COOKIE_DOMAIN") or None
    session_cookie_secure: bool = _bool_env("SESSION_COOKIE_SECURE", False)
    session_cookie_samesite: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
    session_days: int = int(os.getenv("SESSION_DAYS", "3650"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    compile_timeout_seconds: int = int(os.getenv("COMPILE_TIMEOUT_SECONDS", "180"))


settings = Settings()
