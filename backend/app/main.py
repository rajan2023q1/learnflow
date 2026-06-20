"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_all
from .routers import auth

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Production uses Alembic migrations.
    await create_all()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="LearnFlow Authentication & Identity Management API (UC-1).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # required for the HttpOnly refresh cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
