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

# Feature flags
ENABLE_MOCK_INTERVIEW: bool = os.environ.get("ENABLE_MOCK_INTERVIEW", "false").lower() in ("true", "1", "yes")

# Default Provider & URLs
DEFAULT_LLM_PROVIDER: str = os.environ.get("DEFAULT_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "ollama")
DEFAULT_OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://10.134.74.60:11434")

# Per-Provider Concurrency Limits
DEFAULT_CONCURRENCY_LIMITS = {
    "ollama": int(os.environ.get("LLM_CONCURRENCY_OLLAMA", "1")),
    "openai": int(os.environ.get("LLM_CONCURRENCY_OPENAI", "10")),
    "claude": int(os.environ.get("LLM_CONCURRENCY_CLAUDE", "10")),
    "gemini": int(os.environ.get("LLM_CONCURRENCY_GEMINI", "10")),
    "mock": int(os.environ.get("LLM_CONCURRENCY_MOCK", "10")),
}

# Per-Student Rate Limiting
DEFAULT_RATE_LIMIT_REVIEWS_PER_HOUR: int = int(os.environ.get("RATE_LIMIT_REVIEWS_PER_HOUR", "10"))
DEFAULT_RATE_LIMIT_WINDOW_SECONDS: int = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "3600"))
