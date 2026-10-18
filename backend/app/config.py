from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_NAME = "Placement Readiness Copilot"
SECRET_KEY = os.environ.get("SECRET_KEY", "mirai_placement_copilot_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DATA_DIR / 'career_copilot.db'}"
)

SETTINGS_FILE_PATH = DATA_DIR / "settings.json"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
