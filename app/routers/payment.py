from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models import Invoice, Merchant
from app.rpc_client import rpc
from app.services.price import get_rtm_price_usd
from app.config import settings

router = APIRouter()


class InvoiceCreate(BaseModel):
    amount_rtm: float | None = None
    amount_usd: float | None = None
    order_id: str | None = None
    webhook_url: str | None = None


class InvoiceResponse(BaseModel):
    invoice_id: str
    address: str
    amount_rtm: float
    fiat_amount: float | None
    fiat_currency: str = "USD"
    qr_url: str
    expires_in: str
    status: str = "pending"


@router.post("/create", response_model=InvoiceResponse)
def create_invoice(
    invoice_data: InvoiceCreate,
    api_key: str,
    db: Session = Depends(get_db)
):
    # Validate merchant
    merchant = db.query(Merchant).filter(Merchant.api_key == api_key).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Amount logic: prefer RTM if provided, otherwise convert from USD
    if invoice_data.amount_rtm is not None:
        amount_rtm = invoice_data.amount_rtm
        fiat_amount = None
    elif invoice_data.amount_usd is not None:
        rtm_price = get_rtm_price_usd()
        if rtm_price <= 0:
            raise HTTPException(status_code=503, detail="Cannot fetch current RTM price")
        amount_rtm = invoice_data.amount_usd / rtm_price
        fiat_amount = invoice_data.amount_usd
    else:
        raise HTTPException(status_code=400, detail="Provide either amount_rtm or amount_usd")

    # Generate unique address
    try:
        address = rpc.get_new_address(label=f"invoice-{uuid.uuid4().hex[:8]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RPC error: {str(e)}")

    expires_at = datetime.utcnow() + timedelta(minutes=45)

    new_invoice = Invoice(
        id=str(uuid.uuid4()),
        merchant_id=merchant.id,
        address=address,
        amount_requested=amount_rtm,
        fiat_amount=fiat_amount,
        order_id=invoice_data.order_id,
        webhook_url=invoice_data.webhook_url,
        expires_at=expires_at,
        status="pending"
    )

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=raptoreum:{address}?amount={amount_rtm:.8f}"

    return InvoiceResponse(
        invoice_id=new_invoice.id,
        address=address,
        amount_rtm=amount_rtm,
        fiat_amount=fiat_amount,
        qr_url=qr_url,
        expires_in="45 minutes"
    )


@router.get("/{invoice_id}/status")
def get_invoice_status(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "invoice_id": invoice.id,
        "status": invoice.status,
        "amount_requested": invoice.amount_requested,
        "amount_paid": invoice.amount_paid,
        "address": invoice.address,
        "created_at": invoice.created_at.isoformat(),
        "expires_at": invoice.expires_at.isoformat(),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "txid": invoice.txid
    }