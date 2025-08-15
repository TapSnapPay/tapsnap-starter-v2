from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional

from .db import SessionLocal
from . import models

router = APIRouter(prefix="", tags=["public"], include_in_schema=False)
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/checkout", response_class=HTMLResponse)
def checkout_form(
    request: Request,
    merchant_id: int,
    amount: float = 25.00,
    currency: str = "USD",
):
    amount_cents = int(round(amount * 100))
    return templates.TemplateResponse(
        "public/checkout.html",
        {
            "request": request,
            "merchant_id": merchant_id,
            "amount_cents": amount_cents,
            "display_amount": f"{amount:.2f}",
            "currency": currency,
        },
    )

@router.post("/checkout", response_class=HTMLResponse)
def checkout_submit(
    request: Request,
    merchant_id: int = Form(...),
    # accept all the ways the form may send amount
    amount: Optional[float] = Form(None),
    amount_dollars: Optional[float] = Form(None),
    amount_cents: Optional[int] = Form(None),
    currency: str = Form("USD"),
    db: Session = Depends(get_db),
):
    # 1) basic checks
    m = db.get(models.Merchant, merchant_id)
    if not m:
        return templates.TemplateResponse(
            "public/checkout.html",
            {"request": request, "error": "That merchant ID does not exist.", "merchant_id": merchant_id, "currency": currency, "amount": amount},
            status_code=400,
        )

    # 2) normalize the amount
    if amount is None:
        if amount_dollars is not None:
            amount = float(amount_dollars)
        elif amount_cents is not None:
            amount = round((amount_cents or 0) / 100.0, 2)

    # 3) validate amount/currency
    if amount is None or amount <= 0:
        return templates.TemplateResponse(
            "public/checkout.html",
            {"request": request, "error": "Please enter an amount greater than 0.", "merchant_id": merchant_id, "currency": currency},
            status_code=400,
        )

    if currency != "USD":
        return templates.TemplateResponse(
            "public/checkout.html",
            {"request": request, "error": "Only USD is supported right now.", "merchant_id": merchant_id, "currency": currency},
            status_code=400,
        )

    # 4) convert to cents safely
    amount_cents_final = int(round(amount * 100))

    # 5) create the transaction (simulate authorisation)
    tx = models.Transaction(
        merchant_id=merchant_id,
        amount_cents=amount_cents_final,
        currency=currency,
        status="authorised",
        psp_reference="PSP_TEST_PUBLIC",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return RedirectResponse(url=f"/success?tx_id={tx.id}", status_code=303)



@router.get("/success", response_class=HTMLResponse)
def success_page(request: Request):
    return templates.TemplateResponse("public/success.html", {"request": request})


@router.get("/success", response_class=HTMLResponse)
def success_page(
    request: Request,
    tx_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    # Try to load the transaction if a tx_id was provided. If not found, keep tx=None.
    tx = None
    if tx_id is not None:
        tx = db.get(models.Transaction, tx_id)
    return templates.TemplateResponse("public/success.html", {"request": request, "tx": tx})
