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


# ==== Admin IP allow-list + rate limit (simple) ==============================
import os
import time
from collections import deque
from threading import Lock
from typing import Deque, Dict
from fastapi import Request, HTTPException, status

def _client_ip(request: Request) -> str:
    """Get the real client IP (Render sits behind a proxy)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return (request.client.host or "unknown")

# ----- IP allow-list (optional) -----
# ADMIN_IP_ALLOWLIST can be:
# - empty or not set  --> allow all IPs
# - "1.2.3.4,5.6.7.8" --> only these IPs
_ALLOWLIST_RAW = os.getenv("ADMIN_IP_ALLOWLIST", "").strip()
_ALLOWLIST: set[str] = set(ip.strip() for ip in _ALLOWLIST_RAW.split(",") if ip.strip())

def check_admin_ip(request: Request):
    """Block if ADMIN_IP_ALLOWLIST is set and client IP not in it."""
    if not _ALLOWLIST:
        return  # no restriction
    ip = _client_ip(request)
    if ip not in _ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your IP ({ip}) is not allowed.",
        )

# ----- Rate limit (per IP) -----
# ADMIN_RATE_LIMIT examples: "20/m", "100/5m", "30/s"
_RATE_RAW = os.getenv("ADMIN_RATE_LIMIT", "20/m").strip().lower()

def _parse_rate(text: str) -> tuple[int, int]:
    # returns: (limit, window_seconds)
    try:
        num, per = text.split("/")
        limit = int(num)
        if per.endswith("s"):
            window = int(per[:-1])
        elif per.endswith("m"):
            window = int(per[:-1]) * 60
        else:
            window = 60
        return limit, int(window)
    except Exception:
        return 20, 60  # fallback: 20 per 60 seconds

_LIMIT, _WINDOW = _parse_rate(_RATE_RAW)

_hits: Dict[str, Deque[float]] = {}
_hits_lock = Lock()

def rate_limit_admin(request: Request):
    """Simple fixed-window sliding limiter per IP."""
    now = time.time()
    ip = _client_ip(request)
    with _hits_lock:
        dq = _hits.setdefault(ip, deque())
        # drop old timestamps
        while dq and (now - dq[0]) > _WINDOW:
            dq.popleft()
        if len(dq) >= _LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many admin requests. Limit is {_LIMIT} per {_WINDOW}s.",
                headers={"Retry-After": str(_WINDOW)},
            )
        dq.append(now)
