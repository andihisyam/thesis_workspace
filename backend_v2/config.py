import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(REPOSITORY_ROOT / 'data' / 'v2.db').as_posix()}",
    )
    storage_root: Path = Path(
        os.getenv("V2_STORAGE_ROOT", str(REPOSITORY_ROOT / "data" / "v2_storage"))
    ).resolve()
    session_cookie_name: str = "thesis_session"
    session_days: int = int(os.getenv("SESSION_DAYS", "3650"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    compile_timeout_seconds: int = int(os.getenv("COMPILE_TIMEOUT_SECONDS", "180"))


settings = Settings()

