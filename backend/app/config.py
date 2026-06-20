"""Application settings, loaded from environment / .env (pydantic-settings)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LearnFlow Auth"
    environment: str = "development"
    debug: bool = True

    # --- Database -----------------------------------------------------------
    # Zero-config default is SQLite; point at Postgres 17 for production, e.g.
    #   postgresql+asyncpg://user:pass@localhost:5432/learnflow
    database_url: str = "sqlite+aiosqlite:///./learnflow.db"

    # --- Token lifetimes (FR-04, AC-003/009/011) ----------------------------
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    email_verification_ttl_hours: int = 24
    password_reset_ttl_hours: int = 1

    # --- Account lockout (FR-06, AC-004-04) ---------------------------------
    max_failed_logins: int = 5
    failed_login_window_minutes: int = 10
    lockout_minutes: int = 15

    # --- Password hashing (FR-10) -------------------------------------------
    bcrypt_rounds: int = 12

    # --- JWT (NFR-04, AC-007) -----------------------------------------------
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "learnflow"
    jwt_private_key_path: str = "keys/jwt_private.pem"
    jwt_public_key_path: str = "keys/jwt_public.pem"
    # Optional inline PEM (takes precedence over the *_path files when set).
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None

    # --- Refresh-token cookie (NFR-05) --------------------------------------
    refresh_cookie_name: str = "lf_refresh"
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    cookie_domain: str | None = None
    cookie_path: str = "/auth"

    # --- Email / client -----------------------------------------------------
    # Dev convenience for when no email provider is configured yet: mark new
    # accounts as verified on registration so users can log in immediately.
    # NEVER enable in production — it bypasses FR-02 email verification.
    auto_verify_email: bool = False
    email_from: str = "no-reply@learnflow.example"
    frontend_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
