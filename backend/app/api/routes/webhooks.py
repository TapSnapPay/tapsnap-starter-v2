# backend/app/routes/webhooks.py
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import hmac, hashlib, json, os

from ..db import SessionLocal
from .. import models
from ..config import settings
from ..security import require_webhook_auth, webhook_rate_limit  # you added these earlier

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# --- DB session helper --------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Adyen-style webhook endpoint --------------------------------------------
@router.post(
    "/adyen",
    dependencies=[
        Depends(require_webhook_auth),   # Basic Auth: WEBHOOK_USER / WEBHOOK_PASS
        Depends(webhook_rate_limit())    # simple rate-limit you added
    ],
)
async def adyen_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Secured webhook:
    - Basic Auth (already enforced by dependency)
    - HMAC signature check via WEBHOOK_SIGNING_SECRET
    - Idempotency (ignore duplicates)
    - Persist raw event for auditing/replay
    """

    # 1) Read the raw body EXACTLY as sent
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # Normalize headers to lower-case for easy lookups
    hdrs = {k.lower(): v for k, v in request.headers.items()}

    # 2) Verify HMAC SHA-256 signature (header: X-Signature)
    secret = settings.WEBHOOK_SIGNING_SECRET or os.getenv("WEBHOOK_SIGNING_SECRET", "")
    sent_sig = hdrs.get("x-signature", "")
    expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    if not secret or not hmac.compare_digest(sent_sig, expected_sig):
        # if the signature is missing/wrong -> 401
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) Build an idempotency key.
    # Prefer the header "Idempotency-Key"; otherwise hash the body.
    event_key = hdrs.get("idempotency-key", "")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # 4) If we’ve already seen this event_key, return OK quickly (no duplicate work)
    exists = (
        db.query(models.WebhookEvent)
        .filter(models.WebhookEvent.event_key == event_key)
        .first()
    )
    if exists:
        return {"ok": True, "duplicate": True}

    # 5) Persist the raw event for auditing / replay
    evt = models.WebhookEvent(
        provider="adyen",
        event_key=event_key,
        signature_sent=sent_sig,
        raw_json=raw_text,
        headers=json.dumps(hdrs),
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)

    # 6) (Later) do your business logic here (update payment, etc.)
    return {"ok": True, "saved": True}
