"""Test fixtures: an isolated in-memory database and an ASGI HTTP client.

Environment is configured BEFORE the app is imported so settings pick it up.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "keys/test_private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "keys/test_public.pem")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool

# Rebuild the engine on a shared in-memory connection so every session in a test
# sees the same schema/data.
from app import database  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

database.engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.SessionLocal = async_sessionmaker(
    database.engine, expire_on_commit=False, class_=database.AsyncSession
)

from app.database import Base, engine  # noqa: E402
from app.emailer import emailer  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    emailer.outbox.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def outbox():
    return emailer.outbox


# --- helpers ----------------------------------------------------------------
GOOD_PASSWORD = "Str0ng!Pass"


async def register_user(client, email="learner@example.com", password=GOOD_PASSWORD):
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password, "confirm_password": password},
    )


async def register_and_verify(client, outbox, email="learner@example.com", password=GOOD_PASSWORD):
    await register_user(client, email, password)
    token = outbox[-1].token
    await client.post("/auth/verify-email", json={"token": token})
    return email, password
