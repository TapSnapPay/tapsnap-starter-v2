# backend/app/api/routes/webhooks.py

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
import hmac, hashlib, json

from ...db import SessionLocal
from ...config import settings
from ...models import WebhookEvent
from ...security import require_webhook_auth, webhook_rate_limit

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
security = HTTPBasic()

# DB session per-request helper
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/adyen",
             dependencies=[Depends(require_webhook_auth), Depends(webhook_rate_limit())])
async def adyen_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Hardening:
    - Basic Auth (require_webhook_auth)
    - HMAC signature check (X-Signature = hex(hmac_sha256(secret, raw_body)))
    - Idempotency via Idempotency-Key header or SHA256(raw_body)
    - Persist raw payload + headers
    - Return {"ok": True}
    """

    # 1) Read the raw body EXACTLY as received
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # 2) Signature check
    secret = settings.WEBHOOK_SIGNING_SECRET or ""
    expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    sent_sig = request.headers.get("X-Signature", "")

    # fail if missing or mismatch
    if (not secret) or (not hmac.compare_digest(sent_sig, expected_sig)):
        # 401 keeps it consistent with auth failures
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) Idempotency key: prefer header, else hash of body
    event_key = request.headers.get("Idempotency-Key")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # 4) If we’ve already seen this key, return OK quickly (no duplicate work)
    exists = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.event_key == event_key)
        .first()
    )
    if exists:
        return {"ok": True, "duplicate": True}

    # 5) Persist the raw event for auditing/replays
    headers_dict = dict(request.headers)

    evt = WebhookEvent(
        provider="adyen",
        event_key=event_key,
        signature=sent_sig,
        raw_json=raw_text,
        headers=json.dumps(headers_dict),
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)

    # (Optional) business logic: update a payment, etc. — add later
    return {"ok": True}
