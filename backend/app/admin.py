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

from .security import require_admin
from .db import SessionLocal
from . import models

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"  # -> backend/templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    include_in_schema=False,
    dependencies=[Depends(require_admin)]
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

    # ---- NEW: pagination + status filter ----
    per_page = 10

    # page number from the URL, default 1
    try:
        page = int(request.query_params.get("page", "1"))
        if page < 1:
            page = 1
    except Exception:
        page = 1

    # status filter from the URL (optional)
    status = request.query_params.get("status")
    q = db.query(models.Transaction)
    if status:
        q = q.filter(models.Transaction.status == status)

    # count, pages, and one page of results
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
            "status": status,
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
