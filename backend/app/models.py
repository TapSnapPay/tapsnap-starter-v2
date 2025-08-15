from sqlalchemy import String, Integer, DateTime, Enum, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column, Integer, String, Text, DateTime
# (add JSON or UniqueConstraint too if you plan to use them)
from .db import Base
from sqlalchemy import Text
from datetime import datetime

class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    platform_account: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Adyen account code
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="merchant")

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)  # store minor units
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="created")  # created|authorised|captured|refunded|failed
    psp_reference: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship("Merchant", back_populates="transactions")

class Payout(Base):
    __tablename__ = "payouts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="scheduled")  # scheduled|paid|failed
    scheduled_for: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)          # e.g. "adyen"
    event_key = Column(String(128), nullable=False, unique=True)
    signature = Column(String(256), nullable=True)
    raw_json = Column(Text, nullable=False)
    headers = Column(Text, nullable=True)                  # JSON-dumped headers
    created_at = Column(DateTime, default=datetime.utcnow)
