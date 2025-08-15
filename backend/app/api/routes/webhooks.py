# backend/app/api/routes/webhooks.py

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import hmac, hashlib, json, re

from ...db import SessionLocal
from ...config import settings
from ...security import require_webhook_auth, webhook_rate_limit
from ... import models  # Transaction + WebhookEvent live here

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# --- DB session per-request
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
      1) Read raw body
      2) Verify HMAC (X-Signature) with WEBHOOK_SIGNING_SECRET (if set)
      3) Idempotency via Idempotency-Key header (fallback: SHA256(body))
      4) Persist raw event + headers
      5) BUSINESS LOGIC: handle AUTHORISATION -> set Transaction.status / psp_reference
    """
    # -- 1) Read raw body as sent
    raw_bytes: bytes = await request.body()
    raw_text: str = raw_bytes.decode("utf-8", "ignore")

    # -- 2) Signature check (optional, only if a secret is configured)
    secret = settings.WEBHOOK_SIGNING_SECRET or ""
    sent_sig = request.headers.get("X-Signature", "")

    if secret:
        expected_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
        # use compare_digest to avoid timing attacks
        if not hmac.compare_digest(sent_sig, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # -- 3) Idempotency key
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

    # -- 4) Persist the raw event for auditing/replays
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

    # -- 5) BUSINESS LOGIC: update Transaction on AUTHORISATION
    handled = 0
    try:
        payload = json.loads(raw_text) if raw_text else {}
    except json.JSONDecodeError:
        payload = {}

    # Adyen test payload shape:
    # {"notificationItems":[{"NotificationRequestItem":{ ... fields ... }}]}
    items = []
    if isinstance(payload, dict):
        if "notificationItems" in payload and isinstance(payload["notificationItems"], list):
            items = payload["notificationItems"]
        # fallbacks for different shapes (be forgiving)
        elif "NotificationRequestItem" in payload:
            items = [payload]

    for item in items:
        nri = item.get("NotificationRequestItem", item) if isinstance(item, dict) else {}
        event_code = str(nri.get("eventCode", "")).upper()
        success = str(nri.get("success", "")).lower() == "true"
        psp_ref = nri.get("pspReference") or nri.get("psp_reference")
        merchant_ref = str(nri.get("merchantReference", ""))

        # Extract tx_id from merchantReference like "tx_123"
        tx_id = None
        m = re.search(r"tx_(\d+)", merchant_ref)
        if m:
            try:
                tx_id = int(m.group(1))
            except ValueError:
                tx_id = None

        # Update our Transaction only if we can resolve it
        if tx_id is not None and event_code == "AUTHORISATION":
            tx = db.get(models.Transaction, tx_id)
            if tx:
                tx.status = "authorised" if success else "failed"
                if psp_ref:
                    tx.psp_reference = psp_ref

                # If Adyen sends amount in minor units, sync it (optional)
                amt = nri.get("amount", {}) if isinstance(nri.get("amount"), dict) else {}
                if "value" in amt and isinstance(amt["value"], int):
                    tx.amount_cents = int(amt["value"])
                if "currency" in amt and isinstance(amt["currency"], str):
                    tx.currency = amt["currency"]

                db.add(tx)
                handled += 1

    if handled:
        db.commit()

    return {"ok": True, "saved": True, "handled": handled}
