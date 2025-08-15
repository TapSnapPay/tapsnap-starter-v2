# backend/app/config.py
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- Admin auth (already used elsewhere) ----
    ADMIN_USER: str = "admin"
    ADMIN_PASSWORD: str = "password"

    # ---- Webhook basic auth (what your test uses) ----
    WEBHOOK_USER: str = "tapsnap"
    WEBHOOK_PASS: str = "supersecret4321$"

    # ---- NEW: HMAC secret used to verify the webhook body ----
    WEBHOOK_SIGNING_SECRET: Optional[str] = None

    # (optional hardening toggles)
    ADMIN_IP_ALLOWLIST: Optional[str] = None
    ADMIN_RATE_LIMIT: Optional[str] = None

    # DB etc. (leave as-is if you already have these in your env)
    DATABASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def _get_settings() -> Settings:
    return Settings()


settings = _get_settings()
