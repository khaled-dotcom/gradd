from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, DatabaseError
from fastapi import HTTPException

try:
    from backend.src.config import settings
except ImportError:
    from src.config import settings


def _build_database_url() -> str:
    user = quote_plus(settings.DB_USER)
    password = quote_plus(settings.DB_PASS)
    host = settings.DB_HOST
    name = settings.DB_NAME
    return f"mysql+pymysql://{user}:{password}@{host}/{name}"


def _connect_args() -> dict:
    args = {
        "connect_timeout": 10,
        "charset": "utf8mb4",
    }
    if settings.DB_SSL:
        args["ssl"] = {"ssl_mode": "REQUIRED"}
    return args


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    connect_args=_connect_args(),
)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[OK] Database connection successful")
except OperationalError as e:
    print("\n[WARN] Database Connection Warning:")
    print(f"   Cannot connect to MySQL database at {settings.DB_HOST}")
    print(f"   Database: {settings.DB_NAME}")
    print(f"   User: {settings.DB_USER}")
    print(f"   Error: {str(e)}")
    print(f"\n   The application will start, but database operations may fail.\n")
except Exception as e:
    print(f"\n[WARN] Database Connection Warning: {str(e)}\n")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        db.rollback()
        error_msg = str(e)
        print(f"Database connection error: {error_msg}")
        if "Access denied" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database authentication failed. Please check DB_USER and DB_PASS in .env file",
            )
        elif "Unknown database" in error_msg or "doesn't exist" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Database '{settings.DB_NAME}' not found. Please create it first.",
            )
        elif "Can't connect" in error_msg or "Connection refused" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to database at {settings.DB_HOST}. Make sure MySQL is running.",
            )
        else:
            raise HTTPException(status_code=503, detail=f"Database error: {error_msg}")
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while accessing the database: {str(e)}",
        )
    finally:
        db.close()
