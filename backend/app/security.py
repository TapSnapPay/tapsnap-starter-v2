import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# ----- Credentials from env -----
AUTH_USER = "tapsnap"  # admin username is fixed as "tapsnap"
AUTH_PASS = os.getenv("ADMIN_PASSWORD", "")

WEBHOOK_USER = os.getenv("WEBHOOK_USER", "tapsnap")
WEBHOOK_PASS = os.getenv("WEBHOOK_PASS", "")

# ----- Minimal logging so you can confirm what's loaded -----
logging.getLogger().setLevel(logging.INFO)
logging.info(f"[ADMIN] loaded user={AUTH_USER}, pwd_len={len(AUTH_PASS)}")

# The ONLY BasicAuth object we use everywhere
http_basic = HTTPBasic()

def _check(creds: HTTPBasicCredentials, exp_user: str, exp_pass: str) -> None:
    """Reusable checker for Basic auth."""
    if creds.username != exp_user or creds.password != exp_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized",
            headers={"WWW-Authenticate": "Basic"},
        )

def require_admin(credentials: HTTPBasicCredentials = Depends(http_basic)) -> bool:
    """Protects /admin UI."""
    _check(credentials, AUTH_USER, AUTH_PASS)
    return True

def require_webhook(credentials: HTTPBasicCredentials = Depends(http_basic)) -> bool:
    """Protects /webhooks endpoint (already used)."""
    _check(credentials, WEBHOOK_USER, WEBHOOK_PASS)
    return True
