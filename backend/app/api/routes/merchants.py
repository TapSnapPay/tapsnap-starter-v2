from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db import SessionLocal, init_db
from ... import models, schemas
from ...services import adyen

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.MerchantOut)
def create_merchant(payload: schemas.MerchantCreate, db: Session = Depends(get_db)):
    m = models.Merchant(name=payload.name, email=payload.email)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

@router.get("/{merchant_id}", response_model=schemas.MerchantOut)
def get_merchant(merchant_id: int, db: Session = Depends(get_db)):
    m = db.get(models.Merchant, merchant_id)
    if not m:
        raise HTTPException(404, "Merchant not found")
    return m
