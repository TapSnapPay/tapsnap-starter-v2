# backend/app/api/routes/webhooks.py
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
import hmac, hashlib, json, os

from ...db import SessionLocal
from ...models import WebhookEvent
from ...config import settings

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
basic = HTTPBasic()

# --- DB session per request ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Basic auth specifically for webhooks ---
def require_webhook_auth(credentials: HTTPBasicCredentials = Depends(basic)):
    if credentials.username != settings.WEBHOOK_USER or credentials.password != settings.WEBHOOK_PASS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@router.post("/adyen", dependencies=[Depends(require_webhook_auth)])
async def adyen_webhook(request: Request, db: Session = Depends(get_db)):
    # 1) read raw body exactly
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # 2) signature check
    secret = settings.WEBHOOK_SIGNING_SECRET or ""
    sent_sig = request.headers.get("x-signature", "")

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        raw_bytes,
        hashlib.sha256
    ).hexdigest()

    # Fail if missing or mismatch
    if (not secret) or (not hmac.compare_digest(sent_sig, expected_sig)):
        # 401 keeps behavior consistent with other auth failures
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) idempotency key: prefer header, else SHA256(raw body)
    event_key = request.headers.get("Idempotency-Key")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # 4) fast-return if we already stored this
    exists = (
        db.query(WebhookEvent)
          .filter(WebhookEvent.event_key == event_key)
          .first()
    )
    if exists:
        return {"ok": True, "duplicate": True}

    # 5) persist raw event + headers
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

    # 6) (Later) business logic to update payments
    return {"ok": True, "saved": True, "id": evt.id}
