from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
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
    amount: float = Form(...),          # read dollars from the form
    currency: str = Form("USD"),
    db: Session = Depends(get_db),
):
    # --- basic checks ---
    # 1) merchant must exist
    m = db.get(models.Merchant, merchant_id)
    if not m:
        return templates.TemplateResponse(
            "public/checkout.html",
            {
                "request": request,
                "error": "That merchant ID does not exist.",
                "merchant_id": merchant_id,
                "amount": amount,
                "currency": currency,
            },
            status_code=400,
        )

    # 2) amount must be positive
    if amount is None or amount <= 0:
        return templates.TemplateResponse(
            "public/checkout.html",
            {
                "request": request,
                "error": "Please enter an amount greater than 0.",
                "merchant_id": merchant_id,
                "amount": amount,
                "currency": currency,
            },
            status_code=400,
        )

    # 3) allow only USD for now
    if currency not in ("USD",):
        return templates.TemplateResponse(
            "public/checkout.html",
            {
                "request": request,
                "error": "Only USD is supported right now.",
                "merchant_id": merchant_id,
                "amount": amount,
                "currency": currency,
            },
            status_code=400,
        )

    # convert dollars to cents safely
    amount_cents = int(round(amount * 100))

    # create the transaction (simulate authorised)
    tx = models.Transaction(
        merchant_id=merchant_id,
        amount_cents=amount_cents,
        currency=currency,
        status="authorised",
        psp_reference="PSP_TEST_PUBLIC",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return templates.TemplateResponse(
        "public/success.html",
        {"request": request, "tx": tx},
    )


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
