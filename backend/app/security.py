# backend/app/security.py
import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

_basic = HTTPBasic()

def _check_basic(creds: HTTPBasicCredentials, user_env: str, pass_env: str):
    """Reusable checker for BASIC auth."""
    expected_user = os.getenv(user_env, "")
    expected_pass = os.getenv(pass_env, "")
    ok_user = secrets.compare_digest(creds.username or "", expected_user)
    ok_pass = secrets.compare_digest(creds.password or "", expected_pass)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
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
