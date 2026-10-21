from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import PROJECT_NAME
from app.database import engine, Base, ensure_schema_compatibility
from app.logging_config import setup_secure_logging
from app.routers import (
    health,
    auth,
    settings,
    admin,
    chat,
    profile,
    resume_review,
    linkedin_review,
    github_review,
    readiness,
    interview,
    jobs,
    tracker,
    background_jobs,
)

from app.services.job_queue import job_queue_service

# Set up sensitive data redacting for all loggers
setup_secure_logging()
logger = logging.getLogger(__name__)

# Initialize database tables & columns
Base.metadata.create_all(bind=engine)
ensure_schema_compatibility()

app = FastAPI(
    title=PROJECT_NAME,
    description="Placement Readiness Copilot API for MSOT students",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    job_queue_service.cleanup_stale_jobs_on_startup()


# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount application routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(profile.router)
app.include_router(resume_review.router)
app.include_router(linkedin_review.router)
app.include_router(github_review.router)
app.include_router(readiness.router)
app.include_router(interview.router)
app.include_router(jobs.router)
app.include_router(tracker.router)
app.include_router(background_jobs.router)




@app.get("/")
def root():
    return {
        "message": f"Welcome to {PROJECT_NAME} API",
        "health": "/health",
        "docs": "/docs",
    }
