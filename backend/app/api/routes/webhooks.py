from ...security import require_webhook_auth, webhook_rate_limit
from fastapi import Depends
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from ...db import SessionLocal
from ...schemas import WebhookNotification
from ... import models
from ...config import settings
from ...services import adyen
import os, json, hmac, hashlib

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])  # Adyen notifications
security = HTTPBasic()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_basic(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != settings.WEBHOOK_USER or credentials.password != settings.WEBHOOK_PASS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@router.post("/adyen")  # full path: /api/v1/webhooks/adyen
async def adyen_webhook(request: Request, db: Session = Depends(get_db)):
    # 1) Read raw body
    raw_bytes = await request.body()
    raw_text = raw_bytes.decode("utf-8", "ignore")
    headers_dict = dict(request.headers)

    # 2) Signature check (X-Signature is hex(hmac_sha256(secret, raw_body)))
    secret = os.getenv("WEBHOOK_SIGNING_SECRET", "")
    expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    sent_sig = headers_dict.get("x-signature", "")

    # Still keep your Basic Auth if you already had it via a dependency

    if not secret or not hmac.compare_digest(sent_sig, expected_sig):
        # Fail if missing/invalid signature
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) Idempotency key: header first, else hash of body
    event_key = headers_dict.get("idempotency-key")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # 4) If we've already seen this event_key, return OK quickly
    exists = db.query(models.WebhookEvent).filter(models.WebhookEvent.event_key == event_key).first()
    if exists:
        return {"ok": True, "duplicate": True}

    # 5) Save the raw event
    evt = models.WebhookEvent(
        provider="adyen",
        event_key=event_key,
        signature=sent_sig,
        raw_json=raw_text,
        headers=json.dumps(headers_dict),
        status="received",
    )
    db.add(evt)
    db.commit()

    # 6) (Optional) Do your actual business logic here (update a payment, etc.)
    # For now we just say "OK"
    return {"ok": True, "saved": True}
