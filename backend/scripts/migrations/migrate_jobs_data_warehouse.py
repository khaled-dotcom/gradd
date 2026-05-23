"""
Add data-warehouse columns to jobs + import_runs table.
Run: python backend/scripts/migrations/migrate_jobs_data_warehouse.py
"""
import sys
import os
import pymysql

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(os.path.dirname(backend_dir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from backend.src.config import settings
except ImportError:
    from src.config import settings

sys.stdout.reconfigure(encoding="utf-8")

JOB_COLUMNS = [
    ("source", "VARCHAR(50) NULL"),
    ("external_id", "VARCHAR(255) NULL"),
    ("source_url", "VARCHAR(1000) NULL"),
    ("content_hash", "VARCHAR(64) NULL"),
    ("country", "VARCHAR(100) NULL DEFAULT 'Egypt'"),
    ("city", "VARCHAR(100) NULL"),
    ("is_accessible_focus", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
    ("last_seen_at", "DATETIME NULL"),
    ("imported_at", "DATETIME NULL"),
    ("updated_at", "DATETIME NULL"),
]


def migrate():
    conn = pymysql.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        database=settings.DB_NAME,
        charset="utf8mb4",
        ssl={"ssl_mode": "REQUIRED"} if settings.DB_SSL else None,
    )
    try:
        cur = conn.cursor()
        for col, definition in JOB_COLUMNS:
            cur.execute(f"SHOW COLUMNS FROM jobs LIKE '{col}'")
            if not cur.fetchone():
                print(f"Adding jobs.{col}...")
                cur.execute(f"ALTER TABLE jobs ADD COLUMN {col} {definition}")
            else:
                print(f"jobs.{col} exists")

        cur.execute(
            "SHOW INDEX FROM jobs WHERE Key_name = 'uq_jobs_source_external'"
        )
        if not cur.fetchone():
            print("Adding unique index uq_jobs_source_external...")
            cur.execute(
                """
                CREATE UNIQUE INDEX uq_jobs_source_external
                ON jobs (source, external_id)
                """
            )

        cur.execute("SHOW TABLES LIKE 'import_runs'")
        if not cur.fetchone():
            print("Creating import_runs...")
            cur.execute(
                """
                CREATE TABLE import_runs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64) NOT NULL UNIQUE,
                    source VARCHAR(50) NULL,
                    status VARCHAR(20) DEFAULT 'running',
                    added INT DEFAULT 0,
                    `updated` INT DEFAULT 0,
                    deactivated INT DEFAULT 0,
                    errors TEXT NULL,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME NULL,
                    INDEX idx_import_runs_started (started_at)
                )
                """
            )
        else:
            print("import_runs exists")

        conn.commit()
        print("OK — data warehouse migration complete")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
