# backend/app/security.py
import os
import secrets
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from collections import deque
import time

http_basic = HTTPBasic()

# ---- Admin Basic Auth ----
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

async def require_admin(credentials: HTTPBasicCredentials = Depends(http_basic)):
    # Compare in a timing-safe way
    user_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (user_ok and pass_ok):
        # Tell browser to show Basic Auth prompt
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Admin"'},
        )
    return True

# ---- Webhook Basic Auth ----
WEBHOOK_USER = os.getenv("WEBHOOK_USER", "tapsnap")
WEBHOOK_PASS = os.getenv("WEBHOOK_PASS", "supersecret4321$")

async def require_webhook_auth(credentials: HTTPBasicCredentials = Depends(http_basic)):
    user_ok = secrets.compare_digest(credentials.username, WEBHOOK_USER)
    pass_ok = secrets.compare_digest(credentials.password, WEBHOOK_PASS)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Webhook"'},
        )
    return True

# ---- Tiny in-memory rate limiter (per IP) for webhooks ----
_visits = {}  # ip -> deque[timestamps]

def webhook_rate_limit(max_requests: int = 10, window_seconds: int = 60):
    async def _limiter(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        dq = _visits.get(ip)
        if dq is None:
            dq = deque()
            _visits[ip] = dq
        # drop old timestamps outside the window
        while dq and (now - dq[0] > window_seconds):
            dq.popleft()
        dq.append(now)
        if len(dq) > max_requests:
            raise HTTPException(status_code=429, detail="Too many requests")
    return _limiter
