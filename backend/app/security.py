import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

AUTH_USER = "tapsnap"
AUTH_PASS = os.getenv("ADMIN_PASSWORD", "")

# Log only the length for safety
logging.getLogger().setLevel(logging.INFO)
logging.info(f"[ADMIN] loaded user={AUTH_USER}, pwd_len={len(AUTH_PASS)}")

http_basic = HTTPBasic()

def require_admin(credentials: HTTPBasicCredentials = Depends(http_basic)):
    if credentials.username != AUTH_USER or credentials.password != AUTH_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def require_webhook(creds: HTTPBasicCredentials = Depends(_basic)):
    """Protects /webhooks endpoint (already used)."""
    _check_basic(creds, "WEBHOOK_USER", "WEBHOOK_PASS")
    return True

def require_admin(creds: HTTPBasicCredentials = Depends(_basic)):
    """Protects /admin UI."""
    _check_basic(creds, "ADMIN_USER", "ADMIN_PASS")
    return True
