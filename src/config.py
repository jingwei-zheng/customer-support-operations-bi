"""Repository-relative paths and local PostgreSQL settings."""

from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Paths:
    root = PROJECT_ROOT
    raw_mendeley = PROJECT_ROOT / "data" / "raw" / "mendeley_helpdesk"
    processed = PROJECT_ROOT / "data" / "processed"
    sql = PROJECT_ROOT / "sql"
    reports = PROJECT_ROOT / "reports"
    dashboard_exports = PROJECT_ROOT / "dashboard" / "exports"
    logs = PROJECT_ROOT / "logs"


def database_settings() -> dict:
    password = os.getenv("POSTGRES_PASSWORD", "")
    if not password:
        raise RuntimeError("Set POSTGRES_PASSWORD in your local .env before loading PostgreSQL.")
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5433")),
        "dbname": os.getenv("POSTGRES_DB", "customer_ops_bi"),
        "user": os.getenv("POSTGRES_USER", "customer_ops"),
        "password": password,
        "connect_timeout": 10,
        "options": "-c timezone=UTC",
    }
