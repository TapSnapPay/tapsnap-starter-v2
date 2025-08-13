from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import SessionLocal
from . import models

router = APIRouter(prefix="/test", tags=["test"], include_in_schema=False)
templates = Jinja2Templates(directory="templates")

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
    amount_cents: int = Form(...),
    currency: str = Form("USD"),
    db: Session = Depends(get_db),
):
    # Create a transaction and immediately mark as authorised (simulation)
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
