import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    ADYEN_API_KEY: str | None = os.getenv("ADYEN_API_KEY")
    ADYEN_CLIENT_KEY: str | None = os.getenv("ADYEN_CLIENT_KEY")
    ADYEN_MERCHANT_ACCOUNT: str | None = os.getenv("ADYEN_MERCHANT_ACCOUNT")
    ADYEN_HMAC_KEY: str | None = os.getenv("ADYEN_HMAC_KEY")
    ADYEN_ENV: str = os.getenv("ADYEN_ENV", "test")
    ADYEN_LIVE_PREFIX: str | None = os.getenv("ADYEN_LIVE_PREFIX")
    ADYEN_PLATFORM_ACCOUNT: str | None = os.getenv("ADYEN_PLATFORM_ACCOUNT")

    WEBHOOK_USER: str = os.getenv("WEBHOOK_USER", "tapsnap")
    WEBHOOK_PASS: str = os.getenv("WEBHOOK_PASS", "supersecret")

settings = Settings()
