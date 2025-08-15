from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import csv
import io
from fastapi.responses import Response

from .security import require_admin, rate_limit_admin, check_admin_ip
from .db import SessionLocal
from . import models

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"  # -> backend/templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    include_in_schema=False,
    dependencies=[Depends(check_admin_ip), Depends(rate_limit_admin), Depends(require_admin)],
)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_home(request: Request, db: Session = Depends(get_db)):
    # merchants list (unchanged)
    merchants = db.query(models.Merchant).order_by(models.Merchant.id.desc()).all()

    # ---- NEW: pagination + filters ----
    per_page = 10

    # read query params
    qp = request.query_params
    try:
        page = int(qp.get("page", "1"))
        if page < 1:
            page = 1
    except Exception:
        page = 1

    status = qp.get("status") or None
    merchant_id = qp.get("merchant_id") or None
    from_str = qp.get("from") or None
    to_str = qp.get("to") or None

    q = db.query(models.Transaction)

    if status:
        q = q.filter(models.Transaction.status == status)

    if merchant_id:
        try:
            mid = int(merchant_id)
            q = q.filter(models.Transaction.merchant_id == mid)
        except Exception:
            pass

    # date range filtering by created_at
    # from = inclusive midnight; to = inclusive to end-of-day
    if from_str:
        try:
            start = datetime.strptime(from_str, "%Y-%m-%d")
            q = q.filter(models.Transaction.created_at >= start)
        except Exception:
            pass
    if to_str:
        try:
            end = datetime.strptime(to_str, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(models.Transaction.created_at < end)
        except Exception:
            pass

    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    txs = (
        q.order_by(models.Transaction.id.desc())
         .offset((page - 1) * per_page)
         .limit(per_page)
         .all()
    )

    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "merchants": merchants,
            "txs": txs,
            "page": page,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
            # pass filters back to the template so inputs stay filled
            "status": status,
            "merchant_id": merchant_id,
            "from": from_str,
            "to": to_str,
        },
    )

@router.post("/merchants/new", response_class=HTMLResponse)
async def create_merchant(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    if name and email:
        m = models.Merchant(name=name, email=email)
        db.add(m)
        db.commit()
    return RedirectResponse(url="/admin/", status_code=303)

@router.post("/transactions/{tx_id}/refund", response_class=RedirectResponse)
async def refund_tx(
    tx_id: int,
    db: Session = Depends(get_db)
):
    tx = db.get(models.Transaction, tx_id)
    if tx and tx.status != "refunded":
        tx.status = "refunded"
        db.commit()
    return RedirectResponse(url="/admin/", status_code=303)

@router.get("/transactions.csv", dependencies=[Depends(require_admin)])
def export_transactions_csv(
    start: Optional[str] = None,         # format: YYYY-MM-DD
    end: Optional[str] = None,           # format: YYYY-MM-DD (inclusive)
    status: Optional[str] = None,        # e.g. created / authorised / refunded
    merchant_id: Optional[int] = None,   # optional: filter by a single merchant
    db: Session = Depends(get_db),
):
    # Build base query
    q = db.query(models.Transaction)

    # Parse dates safely (YYYY-MM-DD). If invalid, ignore.
    def parse_date(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

    start_dt = parse_date(start)
    end_dt = parse_date(end)

    if start_dt:
        q = q.filter(models.Transaction.created_at >= start_dt)
    if end_dt:
        # make end date inclusive by adding 1 day and using "<"
        q = q.filter(models.Transaction.created_at < (end_dt + timedelta(days=1)))

    if status:
        q = q.filter(models.Transaction.status == status)

    if merchant_id:
        q = q.filter(models.Transaction.merchant_id == merchant_id)

    # Latest first, cap to 500 rows for easy download
    txs = (
        q.order_by(models.Transaction.id.desc())
         .limit(500)
         .all()
    )

    # Build CSV in memory
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "merchant_id", "amount_usd", "currency", "status", "psp_reference", "created_at"])
    for t in txs:
        amount_usd = f"{(t.amount_cents or 0) / 100:.2f}"
        w.writerow([t.id, t.merchant_id, amount_usd, t.currency, t.status, t.psp_reference or "", t.created_at])

    csv_bytes = buf.getvalue()
    headers = {"Content-Disposition": 'attachment; filename="transactions.csv"'}
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

# --- at the very end of backend/app/admin.py ---
admin_ui = router

# --- Transaction detail + Refund button --------------------------------------

from fastapi.responses import RedirectResponse  # already imported at top in your file; keep if present
from fastapi.responses import HTMLResponse      # also already present above

@router.get("/tx/{tx_id}", response_class=HTMLResponse)
def tx_detail(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(models.Transaction, tx_id)
    if not tx:
        # nice 404 page you already have
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404,
        )
    return templates.TemplateResponse(
        "admin/tx_detail.html",
        {"request": request, "tx": tx}
    )

@router.post("/tx/{tx_id}/refund")
def request_refund(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(models.Transaction, tx_id)
    if not tx:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404,
        )

    # Write an audit record
    rr = models.RefundRequest(
        transaction_id=tx.id,
        amount_cents=tx.amount_cents,
        currency=tx.currency,
        requested_by="admin",
        status="refund_requested",
    )
    db.add(rr)

    # Flip the transaction to "refund_requested"
    tx.status = "refund_requested"
    db.add(tx)

    db.commit()
    # back to the tx page with a little query string to show a message
    return RedirectResponse(url=f"/admin/tx/{tx_id}?ok=1", status_code=303)

