# backend/app/api/routes/webhooks.py
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import hmac, hashlib, json, re

from ...db import SessionLocal
from ...config import settings
from ...security import require_webhook_auth, webhook_rate_limit
from ... import models

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# DB session per request
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
    """
    Hardened Adyen webhook:
      1) Read raw body exactly as sent
      2) Verify HMAC (X-Signature) with WEBHOOK_SIGNING_SECRET (if set)
      3) Idempotency via Idempotency-Key header (fallback: SHA256(body))
      4) Persist raw event + headers
      5) BUSINESS: update Transaction on AUTHORISATION / CAPTURE / REFUND
    """

    # 1) Read raw body as sent
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # 2) Signature check (optional, only if a secret is configured)
    secret = settings.WEBHOOK_SIGNING_SECRET or ""
    sent_sig = request.headers.get("X-Signature", "")

    if secret:
        expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
        # use compare_digest to avoid timing attacks
        if not hmac.compare_digest(sent_sig, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3) Idempotency key
    event_key = request.headers.get("Idempotency-Key")
    if not event_key:
        event_key = hashlib.sha256(raw_bytes).hexdigest()

    # Short-circuit if we already saved this exact event (no duplicate work)
    exists = (
        db.query(models.WebhookEvent)
        .filter(models.WebhookEvent.event_key == event_key)
        .first()
    )
    if exists:
        return {"ok": True, "duplicate": True}

    # 4) Persist the raw event for auditing/replays
    headers_dict = dict(request.headers)
    evt = models.WebhookEvent(
        provider="adyen",
        event_key=event_key,
        signature=sent_sig,
        raw_json=raw_text,
        headers=json.dumps(headers_dict),
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)

    # 5) BUSINESS: update Transaction on AUTHORISATION / CAPTURE / REFUND
    handled = 0

    # Turn the raw JSON text into a Python dict (or {} if it’s not JSON)
    try:
        payload = json.loads(raw_text) if raw_text else {}
    except json.JSONDecodeError:
        payload = {}

    # Helper: yield each NotificationRequestItem, no matter the shape
    def notification_items(p):
        if isinstance(p, dict):
            if "notificationItems" in p and isinstance(p["notificationItems"], list):
                for wrapper in p["notificationItems"]:
                    if isinstance(wrapper, dict) and "NotificationRequestItem" in wrapper:
                        yield wrapper["NotificationRequestItem"]
                    else:
                        yield wrapper
            elif "NotificationRequestItem" in p:
                yield p["NotificationRequestItem"]
            else:
                yield p
        elif isinstance(p, list):
            for item in p:
                yield item

    # Walk the items and update our Transaction
    for nri in notification_items(payload):
        nri = nri or {}
        event_code = str(nri.get("eventCode", "")).upper()
        success = str(nri.get("success", "")).lower() == "true"
        psp_ref = nri.get("pspReference") or nri.get("psp_reference")
        merchant_ref = str(nri.get("merchantReference", ""))

        # Find tx_id inside merchantReference like "tx_123"
        m = re.search(r"tx_(\d+)", merchant_ref)
        if not m:
            continue
        try:
            tx_id = int(m.group(1))
        except ValueError:
            continue

        tx = db.get(models.Transaction, tx_id)
        if not tx:
            continue

        # --- AUTHORISATION ---
        if event_code == "AUTHORISATION":
            tx.status = "authorised" if success else "failed"
            if psp_ref:
                tx.psp_reference = psp_ref
            # If Adyen sent amount in minor units, sync it (optional)
            amt = nri.get("amount") or {}
            if isinstance(amt, dict):
                if isinstance(amt.get("value"), int):
                    tx.amount_cents = int(amt["value"])
                if isinstance(amt.get("currency"), str):
                    tx.currency = amt["currency"]
            db.add(tx)
            handled += 1
            continue

        # --- CAPTURE ---
        if event_code == "CAPTURE":
            tx.status = "captured" if success else "failed"
            if psp_ref:
                tx.psp_reference = psp_ref
            db.add(tx)
            handled += 1
            continue

        # --- REFUND ---
if event_code == "REFUND":
    if success:
        tx.status = "refunded"
        if psp_ref:
            tx.psp_reference = psp_ref

        # NEW: mark the newest refund row for this tx as refunded
        rf = (
            db.query(models.Refund)
            .filter(models.Refund.tx_id == tx.id)
            .order_by(models.Refund.id.desc())
            .first()
        )
        if rf:
            rf.status = "refunded"
            if psp_ref:
                rf.psp_reference = psp_ref
            db.add(rf)

    else:
        # refund failed
        if psp_ref:
            tx.psp_reference = psp_ref

        # optionally mark the latest refund row as failed
        rf = (
            db.query(models.Refund)
            .filter(models.Refund.tx_id == tx.id)
            .order_by(models.Refund.id.desc())
            .first()
        )
        if rf:
            rf.status = "failed"
            if psp_ref:
                rf.psp_reference = psp_ref
            db.add(rf)

    db.add(tx)
    handled += 1


    # Save DB changes only if we actually touched something
    if handled:
        db.commit()

    return {"ok": True, "saved": True, "handled": handled}
