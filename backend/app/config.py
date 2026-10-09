import os
from pathlib import Path
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'sla_db.db').as_posix()}"


class Settings(BaseSettings):
    # SQLite selalu menunjuk ke database di folder backend, sehingga aplikasi
    # tidak membuat database baru ketika dijalankan dari working directory lain.
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    PROJECT_NAME: str = "SLA Monitoring Dashboard"


settings = Settings()
