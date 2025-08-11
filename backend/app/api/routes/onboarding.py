from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...db import SessionLocal
from ...services import adyen

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/start")
def start_onboarding(business_type: str = "sole", db: Session = Depends(get_db)):
    # TODO: Accept real business details, forward to Adyen Balance Platform
    res = adyen.create_platform_account({"businessType": business_type})
    return res
