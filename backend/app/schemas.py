from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

class MerchantCreate(BaseModel):
    name: str
    email: EmailStr

class MerchantOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    platform_account: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class TransactionCreate(BaseModel):
    merchant_id: int
    amount_cents: int = Field(gt=0)
    currency: str = "USD"

class TransactionOut(BaseModel):
    id: int
    merchant_id: int
    amount_cents: int
    currency: str
    status: str
    psp_reference: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class WebhookNotification(BaseModel):
    live: str
    notificationItems: list
