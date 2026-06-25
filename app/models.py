from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from .database import Base
import uuid


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    
    address = Column(String(255), nullable=False, index=True)
    amount_requested = Column(Float, nullable=False)           # in RTM
    amount_paid = Column(Float, default=0.0)
    fiat_amount = Column(Float, nullable=True)                 # approximate USD at creation
    fiat_currency = Column(String(10), default="USD")
    
    order_id = Column(String(255), nullable=True)                   # merchant's internal reference
    webhook_url = Column(String(500), nullable=True)
    
    status = Column(String(50), default="pending")                 # pending / paid / expired / underpaid
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    txid = Column(String(255), nullable=True)                       # last detected tx (for reference)