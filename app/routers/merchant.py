from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import uuid
import secrets
import io
import csv
from datetime import datetime

from app.database import get_db
from app.models import Merchant, Invoice
from app.limiter import limiter
from app.config import settings

router = APIRouter()

class MerchantCreate(BaseModel):
    email: EmailStr

@router.post("/create")
@limiter.limit("10/minute")
def create_merchant(request: Request, merchant_data: MerchantCreate, db: Session = Depends(get_db)):
    existing = db.query(Merchant).filter(Merchant.email == merchant_data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    api_key = secrets.token_urlsafe(32)
    
    new_merchant = Merchant(
        id=str(uuid.uuid4()),
        email=merchant_data.email,
        api_key=api_key
    )
    
    db.add(new_merchant)
    db.commit()
    db.refresh(new_merchant)
    
    return {
        "message": "Merchant created",
        "api_key": api_key,
        "email": merchant_data.email
    }

@router.get("/me")
def get_current_merchant(api_key: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.api_key == api_key).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return {
        "id": merchant.id,
        "email": merchant.email,
        "active": merchant.is_active
    }

@router.get("/invoices")
def get_merchant_invoices(api_key: str, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.api_key == api_key).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Cap page size to prevent abuse
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    
    invoices = db.query(Invoice).filter(Invoice.merchant_id == merchant.id).order_by(Invoice.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": inv.id,
            "address": inv.address,
            "amount_requested": inv.amount_requested,
            "amount_paid": inv.amount_paid,
            "fiat_amount": inv.fiat_amount,
            "fiat_currency": inv.fiat_currency,
            "order_id": inv.order_id,
            "webhook_url": inv.webhook_url,
            "status": inv.status,
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat(),
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "txid": inv.txid
        } for inv in invoices
    ]

@router.post("/rotate-key")
def rotate_merchant_key(api_key: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.api_key == api_key).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    new_key = secrets.token_urlsafe(32)
    merchant.api_key = new_key
    db.commit()
    
    return {
        "message": "API key rotated successfully",
        "new_api_key": new_key
    }

@router.get("/export")
def export_merchant_data(api_key: str, format: str = "json", db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.api_key == api_key).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if format.lower() == "csv":
        def csv_generator():
            output = io.StringIO()
            writer = csv.writer(output)
            # Write headers
            writer.writerow([
                "Invoice ID", "Address", "RTM Requested", "RTM Paid", 
                "USD Value", "Order ID", "Webhook URL", "Status", 
                "Created At", "Paid At", "TXID"
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Query and yield in chunks of 100
            query = db.query(Invoice).filter(Invoice.merchant_id == merchant.id).order_by(Invoice.created_at.desc())
            for inv in query.yield_per(100):
                writer.writerow([
                    inv.id, inv.address, inv.amount_requested, inv.amount_paid,
                    inv.fiat_amount or "", inv.order_id or "", inv.webhook_url or "", inv.status,
                    inv.created_at.isoformat(), inv.paid_at.isoformat() if inv.paid_at else "", inv.txid or ""
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        return StreamingResponse(
            csv_generator(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=raptoreumpay_export.csv"}
        )
    else:
        # Cap JSON export to the latest 500 records to prevent memory issues
        invoices = db.query(Invoice).filter(Invoice.merchant_id == merchant.id).order_by(Invoice.created_at.desc()).limit(500).all()
        return {
            "merchant_email": merchant.email,
            "exported_at": datetime.utcnow().isoformat(),
            "invoices": [
                {
                    "id": inv.id,
                    "address": inv.address,
                    "amount_requested": inv.amount_requested,
                    "amount_paid": inv.amount_paid,
                    "fiat_amount": inv.fiat_amount,
                    "order_id": inv.order_id,
                    "webhook_url": inv.webhook_url,
                    "status": inv.status,
                    "created_at": inv.created_at.isoformat(),
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                    "txid": inv.txid
                } for inv in invoices
            ]
        }