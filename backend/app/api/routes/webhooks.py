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

@router.post("/adyen")
async def adyen_notifications(payload: WebhookNotification, request: Request, ok: bool = Depends(require_basic), db: Session = Depends(get_db)):
    # Validate HMAC (stubbed true in dev)
    if not adyen.verify_hmac(settings.ADYEN_HMAC_KEY or "", payload.__dict__):
        raise HTTPException(400, "Invalid signature")

    # Minimal handler: record AUTHORISATION results
    for item in payload.notificationItems:
        event = item.get("NotificationRequestItem", {})
        eventCode = event.get("eventCode")
        success = event.get("success") in (True, "true", "True")  # Adyen sends string
        pspRef = event.get("pspReference")
        amount = event.get("amount", {}).get("value") or 0
        currency = event.get("amount", {}).get("currency") or "USD"
        merchant_ref = event.get("merchantReference")  # we can encode our tx_id here (e.g., "tx_123")

        if eventCode == "AUTHORISATION" and merchant_ref and str(merchant_ref).startswith("tx_"):
            try:
                tx_id = int(str(merchant_ref).split("_")[1])
                t = db.get(models.Transaction, tx_id)
                if t:
                    t.status = "authorised" if success else "failed"
                    t.psp_reference = pspRef
                    db.commit()
            except Exception:
                pass

    return {"status": "received"}

@router.post("/adyen", dependencies=[Depends(require_webhook_auth), Depends(webhook_rate_limit())])
async def adyen_webhook(payload: dict, request: Request):
    # ... existing logic ...
    return {"received": True}

