import os
import platform
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "汇安检测"
    database_url: str = "sqlite:///./inspection_ai.db"
    upload_dir: Path = Path("app/storage/uploads")
    report_dir: Path = Path("app/reports")
    ocr_provider: str = "cascade"
    document_parser_provider: str = "auto"
    mineru_command: str = ""
    mineru_timeout_seconds: int = 180
    model_provider: str = "litellm-compatible"
    litellm_base_url: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    desktop_mode = os.environ.get("HUIAN_DESKTOP") == "1"
    system_name = platform.system()
    if (desktop_mode or system_name == "Windows") and settings.database_url == "sqlite:///./inspection_ai.db":
        if system_name == "Windows":
            base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif system_name == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        else:
            base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        data_dir = base_dir / "HuianInspectionAI"
        data_dir.mkdir(parents=True, exist_ok=True)
        database_path = data_dir / "inspection_ai.db"
        if desktop_mode and not database_path.exists():
            seed_db = _bundled_seed_database_path()
            if seed_db.exists():
                shutil.copy2(seed_db, database_path)
        settings.database_url = f"sqlite:///{database_path.as_posix()}"
        if settings.upload_dir == Path("app/storage/uploads"):
            settings.upload_dir = data_dir / "uploads"
        if settings.report_dir == Path("app/reports"):
            settings.report_dir = data_dir / "reports"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    return settings


def _bundled_seed_database_path() -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidates = [
        bundle_root / "app" / "seed" / "inspection_ai_seed.db",
        Path(__file__).resolve().parent / "seed" / "inspection_ai_seed.db",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
