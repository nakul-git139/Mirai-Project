from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_NAME = "Placement Readiness Copilot"
APP_ENV: str = os.environ.get("APP_ENV", "development").strip().lower()

import hashlib

# SHA-256 fingerprint of the deprecated, compromised legacy development secret key
COMPROMISED_DEV_DIGEST = "7e681cd940c1f69e02fe3cfbe44dec4302adac1e0e5573a21c10b0deddf41927"


def resolve_secret_key(
    app_env: str = APP_ENV,
    env_file: Path | None = None,
    backend_env_file: Path | None = None,
) -> str:
    """
    Resolves SECRET_KEY strictly from the environment or .env file.
    - In production (APP_ENV=production): refuses to start if missing or compromised.
    - In development: auto-generates a secure random key and persists to gitignored .env.
    - Rejects the deprecated legacy dev key as compromised.
    """
    root_env = env_file if env_file is not None else (BASE_DIR.parent / ".env")
    back_env = backend_env_file if backend_env_file is not None else (BASE_DIR / ".env")

    raw_key = os.environ.get("SECRET_KEY", "").strip()

    # Check .env files if not set in os.environ
    if not raw_key:
        for ef in [root_env, back_env]:
            if ef.exists():
                try:
                    with open(ef, "r", encoding="utf-8") as f:
                        for line in f:
                            s_line = line.strip()
                            if s_line.startswith("SECRET_KEY=") and not s_line.startswith("SECRET_KEY=#"):
                                val = s_line.split("=", 1)[1].strip().strip('"').strip("'")
                                if val:
                                    raw_key = val
                                    os.environ["SECRET_KEY"] = raw_key
                                    break
                except Exception:
                    pass
            if raw_key:
                break

    # Guard against compromised legacy key
    if raw_key and hashlib.sha256(raw_key.encode("utf-8")).hexdigest() == COMPROMISED_DEV_DIGEST:
        raise RuntimeError(
            "FATAL: The provided SECRET_KEY matches the deprecated, compromised default key. "
            "Please generate a new cryptographically secure random secret key."
        )

    if raw_key:
        return raw_key

    # Missing key handling
    if app_env == "production":
        raise RuntimeError(
            "FATAL: SECRET_KEY environment variable is required when APP_ENV=production. "
            "Refusing to start application in production without an explicit secure secret key."
        )

    # Development mode: auto-generate random 32-byte urlsafe key and persist to gitignored .env
    import secrets
    generated = secrets.token_urlsafe(32)
    os.environ["SECRET_KEY"] = generated
    try:
        with open(root_env, "a", encoding="utf-8") as f:
            f.write(f"\n# Auto-generated development key\nSECRET_KEY={generated}\n")
    except Exception:
        pass

    return generated


SECRET_KEY = resolve_secret_key()
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
DEFAULT_OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

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

# Per-Job Maximum Execution Run Time (Safety Net Watchdog)
DEFAULT_JOB_MAX_RUN_TIME_SECONDS: int = int(os.environ.get("JOB_MAX_RUN_TIME_SECONDS", "300"))

