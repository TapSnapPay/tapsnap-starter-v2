from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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
    ...
    merchants = db.query(models.Merchant).order_by(models.Merchant.id.desc()).all()
    txs = db.query(models.Transaction).order_by(models.Transaction.id.desc()).limit(50).all()
    return templates.TemplateResponse("admin/index.html", {"request": request, "merchants": merchants, "txs": txs})

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

@router.get("/transactions.csv", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def export_transactions_csv(db: Session = Depends(get_db)):
    # Grab up to the latest 500 transactions (change if you like)
    txs = (
        db.query(models.Transaction)
        .order_by(models.Transaction.id.desc())
        .limit(500)
        .all()
    )

    # Build CSV in memory (safe for a few thousand rows)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")

    # Header row
    w.writerow(["id", "merchant_id", "amount_usd", "currency", "status", "psp_reference", "created_at"])

    # Data rows
    for t in txs:
        amount_usd = f"{(t.amount_cents or 0) / 100:.2f}"
        w.writerow([
            t.id,
            t.merchant_id,
            amount_usd,
            t.currency,
            t.status,
            t.psp_reference or "",
            t.created_at,
        ])

    csv_bytes = buf.getvalue()
    headers = {"Content-Disposition": 'attachment; filename="transactions.csv"'}
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

