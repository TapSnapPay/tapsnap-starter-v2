# backend/app/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# ---------- Merchants ----------
class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    platform_account: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="merchant")

# ---------- Transactions ----------
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="created")  # created|authorised|captured|refunded|failed
    psp_reference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship("Merchant", back_populates="transactions")

# ---------- Payouts ----------
class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="scheduled")  # scheduled|paid|failed
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---------- Webhook raw events ----------
class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "adyen"
    event_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)  # idempotency key
    signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)       # hex HMAC (if sent)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)                        # raw request body
    headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                # JSON-dumped headers
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
