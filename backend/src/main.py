from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.src.db.database import engine, Base
from backend.src.config import settings
from backend.src.routes import (
    jobs,
    users,
    chat,
    applications,
    disabilities,
    tools,
    security,
    companies,
    cv,
    analytics,
    files,
)

try:
    from backend.src.routes import action_recognition
except ImportError:
    action_recognition = None
from sqlalchemy.exc import OperationalError
import os

try:
    Base.metadata.create_all(bind=engine)
except OperationalError as e:
    print(f"\n[WARN] Could not create database tables: {e}")
    print("   The application will start, but database operations may fail.")
    print("   Please check your database connection settings.\n")

app = FastAPI(title="EmpowerWork - Job Assistance System")

_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if not _origins or _origins == ["*"]:
    _allow_origins = ["*"]
else:
    _allow_origins = _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(applications.router)
app.include_router(disabilities.router)
app.include_router(tools.router)
app.include_router(security.router)
app.include_router(companies.router)
app.include_router(cv.router)
if action_recognition is not None:
    app.include_router(action_recognition.router)
app.include_router(analytics.router)
app.include_router(files.router)

if os.path.exists("uploads") and not settings.AZURE_STORAGE_CONNECTION_STRING:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads_static")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "EmpowerWork API is running",
        "events_enabled": settings.EVENTS_ENABLED,
        "blob_storage": bool(settings.AZURE_STORAGE_CONNECTION_STRING),
    }


@app.get("/")
def root():
    return {
        "message": "EmpowerWork API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
