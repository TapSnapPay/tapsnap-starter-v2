# backend/app/api/routes/webhooks.py
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import hmac, hashlib, json

from ...db import SessionLocal
from ...models import WebhookEvent
from ...config import settings
from ...security import require_webhook_auth, webhook_rate_limit

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/adyen",
    dependencies=[Depends(require_webhook_auth), Depends(webhook_rate_limit())],
)
async def adyen_webhook(request: Request, db: Session = Depends(get_db)):
    # 1) Read the exact body (bytes)
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # 2) Verify HMAC (optional – only if secret is set)
    secret = settings.WEBHOOK_SIGNING_SECRET or ""
    sent_sig = request.headers.get("X-Signature", "")

    if secret:
        expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sent_sig, expected_sig):
            # 401 keeps it consistent with earlier behavior
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) Idempotency key: prefer header, else hash(body)
    event_key = request.headers.get("Idempotency-Key")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # 4) Fast duplicate check
    exists = (
        db.query(WebhookEvent)
          .filter(WebhookEvent.event_key == event_key)
          .first()
    )
    if exists:
        return {"ok": True, "duplicate": True}

    # 5) Persist raw event + headers
    headers_dict = dict(request.headers)

    evt = WebhookEvent(
        provider="adyen",
        event_key=event_key,
        signature=sent_sig or None,
        raw_json=raw_text,
        headers=json.dumps(headers_dict),
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)

    # 6) (Later) do business logic here (e.g., update a payment)
    return {"ok": True}
