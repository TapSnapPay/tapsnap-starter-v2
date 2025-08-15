# backend/app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # --- Admin auth (already working) ---
    ADMIN_PASSWORD: str = Field(..., env="ADMIN_PASSWORD")

    # Optional hardening knobs (safe defaults)
    ADMIN_RATE_LIMIT: int = Field(60, env="ADMIN_RATE_LIMIT")
    ADMIN_IP_ALLOWLIST: str = Field("", env="ADMIN_IP_ALLOWLIST")

    # --- Webhook basic auth ---
    WEBHOOK_USER: str = Field("", env="WEBHOOK_USER")
    WEBHOOK_PASS: str = Field("", env="WEBHOOK_PASS")

    # --- NEW: Webhook HMAC secret (this is what was missing) ---
    # If set, we will verify X-Signature = hex(hmac_sha256(secret, raw_body))
    WEBHOOK_SIGNING_SECRET: str | None = Field(None, env="WEBHOOK_SIGNING_SECRET")

    class Config:
        # Optional .env support; env vars from Render still win
        env_file = ".env"
        extra = "ignore"  # ignore any extra envs you might have

settings = Settings()
