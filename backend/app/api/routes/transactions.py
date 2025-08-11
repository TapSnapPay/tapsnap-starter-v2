from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db import SessionLocal
from ... import models, schemas

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.TransactionOut)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    merchant = db.get(models.Merchant, payload.merchant_id)
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    t = models.Transaction(merchant_id=payload.merchant_id, amount_cents=payload.amount_cents, currency=payload.currency)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@router.get("/", response_model=list[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.id.desc()).all()

@router.post("/{tx_id}/confirm", response_model=schemas.TransactionOut)
def confirm_transaction(tx_id: int, psp_reference: str, status: str = "authorised", db: Session = Depends(get_db)):
    t = db.get(models.Transaction, tx_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    t.status = status
    t.psp_reference = psp_reference
    db.commit()
    db.refresh(t)
    return t
