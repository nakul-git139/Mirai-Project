from __future__ import annotations
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema_compatibility():
    """Ensures newly added columns exist in existing SQLite databases."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(review_results)")).fetchall()
            cols = [r[1] for r in res] if res else []
            if cols and "rewrites" not in cols:
                conn.execute(text("ALTER TABLE review_results ADD COLUMN rewrites JSON"))
                conn.commit()
        except Exception:
            pass

        try:
            res = conn.execute(text("PRAGMA table_info(interview_sessions)")).fetchall()
            cols = [r[1] for r in res] if res else []
            if cols:
                if "duration_minutes" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN duration_minutes INTEGER DEFAULT 15"))
                if "time_limit_seconds" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN time_limit_seconds INTEGER DEFAULT 900"))
                if "expires_at" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN expires_at DATETIME"))
                if "current_question_index" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN current_question_index INTEGER DEFAULT 0"))
                if "question_plan" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN question_plan JSON"))
                if "rubric_scores" not in cols:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN rubric_scores JSON"))
                conn.commit()
        except Exception:
            pass

        try:
            res = conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
            cols = [r[1] for r in res] if res else []
            if cols:
                if "job_type" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN job_type VARCHAR(50) DEFAULT 'job'"))
                if "eligibility_criteria" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN eligibility_criteria JSON"))
                if "is_pinned" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN is_pinned BOOLEAN DEFAULT 1"))
                if "deadline" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN deadline VARCHAR(100)"))
                conn.commit()
        except Exception:
            pass

        try:
            res = conn.execute(text("PRAGMA table_info(applications)")).fetchall()
            cols = [r[1] for r in res] if res else []
            if cols:
                if "company" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN company VARCHAR(255)"))
                if "role" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN role VARCHAR(255)"))
                if "link" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN link VARCHAR(500)"))
                if "last_status_change_at" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN last_status_change_at DATETIME"))
                if "status_history" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN status_history JSON"))
                if "followup_reminder_days" not in cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN followup_reminder_days INTEGER DEFAULT 7"))
                conn.commit()
        except Exception:
            pass



def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

