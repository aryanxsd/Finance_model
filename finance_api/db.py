import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app, g

from .config import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, STATUS_ACTIVE


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def query_all(query: str, params: tuple = ()) -> list[dict]:
    cursor = get_db().execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    return rows


def query_one(query: str, params: tuple = ()) -> dict | None:
    cursor = get_db().execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def execute(query: str, params: tuple = ()) -> int:
    cursor = get_db().execute(query, params)
    get_db().commit()
    lastrowid = cursor.lastrowid
    cursor.close()
    return lastrowid


def init_db() -> None:
    database = get_db()
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('viewer', 'analyst', 'admin')),
            status TEXT NOT NULL CHECK(status IN ('active', 'inactive')),
            api_token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS financial_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK(amount >= 0),
            record_type TEXT NOT NULL CHECK(record_type IN ('income', 'expense')),
            category TEXT NOT NULL,
            record_date TEXT NOT NULL,
            notes TEXT,
            created_by INTEGER NOT NULL,
            updated_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0, 1)),
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(updated_by) REFERENCES users(id)
        );
        """
    )
    database.commit()
    seed_default_users()
    seed_default_records()


def seed_default_users() -> None:
    existing = query_one("SELECT id FROM users LIMIT 1")
    if existing:
        return

    timestamp = utc_now()
    seed_users = [
        (
            "Vihaan Viewer",
            "viewer@finance.local",
            ROLE_VIEWER,
            STATUS_ACTIVE,
            "viewer-token",
            timestamp,
            timestamp,
        ),
        (
            "Anaya Analyst",
            "analyst@finance.local",
            ROLE_ANALYST,
            STATUS_ACTIVE,
            "analyst-token",
            timestamp,
            timestamp,
        ),
        (
            "Aarav Admin",
            "admin@finance.local",
            ROLE_ADMIN,
            STATUS_ACTIVE,
            "admin-token",
            timestamp,
            timestamp,
        ),
    ]

    get_db().executemany(
        """
        INSERT INTO users (name, email, role, status, api_token, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        seed_users,
    )
    get_db().commit()


def seed_default_records() -> None:
    existing = query_one("SELECT id FROM financial_records LIMIT 1")
    admin = query_one("SELECT id FROM users WHERE role = ?", (ROLE_ADMIN,))
    if existing or not admin:
        return

    admin_id = admin["id"]
    timestamp = utc_now()
    seed_records = [
        (12500.0, "income", "Salary", "2026-03-05", "Monthly salary", admin_id, admin_id, timestamp, timestamp),
        (1800.0, "expense", "Rent", "2026-03-06", "Apartment rent", admin_id, admin_id, timestamp, timestamp),
        (2500.0, "income", "Freelance", "2026-03-11", "API consulting", admin_id, admin_id, timestamp, timestamp),
        (450.5, "expense", "Utilities", "2026-03-12", "Electricity and internet", admin_id, admin_id, timestamp, timestamp),
        (920.0, "expense", "Travel", "2026-02-20", "Client meeting travel", admin_id, admin_id, timestamp, timestamp),
        (3800.0, "income", "Bonus", "2026-02-28", "Quarterly performance bonus", admin_id, admin_id, timestamp, timestamp),
    ]
    get_db().executemany(
        """
        INSERT INTO financial_records (
            amount, record_type, category, record_date, notes, created_by, updated_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        seed_records,
    )
    get_db().commit()
