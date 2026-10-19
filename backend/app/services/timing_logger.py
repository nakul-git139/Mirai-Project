from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import LLMTimingLog

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TIMING_JSONL_PATH = DATA_DIR / "llm_timing.jsonl"


def log_llm_timing(
    feature: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    output_tokens: int,
    duration_seconds: float,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Records latency, tokens, and metadata for an LLM invocation.
    Persists to SQLite database and appends to data/llm_timing.jsonl.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    meta_dict = metadata or {}

    # 1. Append to JSONL log file
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "timestamp": now_iso,
            "feature": feature,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "duration_seconds": round(duration_seconds, 3),
            "status": status,
            "metadata": meta_dict,
        }
        with open(TIMING_JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.warning(f"Failed to append to timing JSONL log: {e}")

    # 2. Persist to SQLite database table
    try:
        db: Session = SessionLocal()
        try:
            entry = LLMTimingLog(
                feature=feature,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                output_tokens=output_tokens,
                duration_seconds=duration_seconds,
                status=status,
                metadata_json=json.dumps(meta_dict),
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to persist timing log to database: {e}")


def get_recent_timing_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent timing logs from SQLite database with JSONL fallback."""
    results: List[Dict[str, Any]] = []
    try:
        db: Session = SessionLocal()
        try:
            records = (
                db.query(LLMTimingLog)
                .order_by(LLMTimingLog.created_at.desc())
                .limit(limit)
                .all()
            )
            for r in records:
                meta = {}
                if r.metadata_json:
                    try:
                        meta = json.loads(r.metadata_json)
                    except Exception:
                        pass
                results.append({
                    "id": r.id,
                    "feature": r.feature,
                    "provider": r.provider,
                    "model": r.model,
                    "prompt_tokens": r.prompt_tokens,
                    "output_tokens": r.output_tokens,
                    "duration_seconds": r.duration_seconds,
                    "status": r.status,
                    "metadata": meta,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                })
            return results
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database query for timing logs failed, falling back to JSONL: {e}")

    # Fallback to reading JSONL
    if TIMING_JSONL_PATH.exists():
        try:
            with open(TIMING_JSONL_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in reversed(lines[-limit:]):
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        except Exception:
            pass

    return results
