"""Async SQLAlchemy engine, session factory, and declarative base."""

from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


def utcnow() -> datetime:
    """Naive UTC timestamp — used consistently so comparisons work on both
    SQLite (which drops tzinfo) and Postgres."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# SQLite needs check_same_thread disabled for the async driver; Postgres ignores it.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_async_engine(settings.database_url, future=True, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def create_all() -> None:
    """Create tables if they do not exist. Production should use Alembic."""
    from . import models  # noqa: F401  (ensure models are registered)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
