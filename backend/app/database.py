"""Database configuration for the test efficiency platform.

Default backend is MySQL (host=127.0.0.1, port=3306, db=test_efficiency_platform,
user=root, password=root). Override with DB_* environment variables. Set
DB_BACKEND=sqlite to fall back to the bundled SQLite file (used by older setups).
"""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "platform.db")
DB_BACKEND = os.getenv("DB_BACKEND", "mysql").lower()

if DB_BACKEND == "mysql":
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "test_efficiency_platform")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/"
        f"{DB_NAME}?charset=utf8mb4"
    )
    engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)
else:
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """Add new columns to existing SQLite tables (create_all won't alter tables)."""
    if DB_BACKEND != "sqlite":
        return  # MySQL 表结构变更请走 ALTER TABLE / Navicat
    needed = {
        "run_details": {"extracted": "TEXT"},
    }
    with engine.connect() as conn:
        for table, cols in needed.items():
            try:
                existing = {row[1] for row in conn.execute(
                    text(f"PRAGMA table_info({table})")
                ).fetchall()}
            except Exception:
                continue
            for col, coltype in cols.items():
                if col not in existing:
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
                        conn.commit()
                    except Exception:
                        pass  # column may have been added by another worker
