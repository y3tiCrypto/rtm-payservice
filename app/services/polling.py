from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
import requests
import logging
import hmac
import hashlib
import json
import time

from app.database import SessionLocal
from app.models import Invoice, Merchant
from app.rpc_client import rpc

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.start()


def check_pending_invoices():
    """Background task: poll all pending invoices every 30 seconds"""
    db = SessionLocal()
    try:
        pending = db.query(Invoice).filter(
            Invoice.status == "pending",
            Invoice.expires_at > datetime.utcnow()
        ).all()

        for invoice in pending:
            try:
                received = rpc.get_received_by_address(invoice.address, minconf=0)
                
                if received >= invoice.amount_requested * 0.98:  # 2% tolerance for dust/rounding
                    invoice.status = "paid"
                    invoice.amount_paid = received
                    invoice.paid_at = datetime.utcnow()
                    
                    # Try to get txid (simplistic - first tx that sent to this address)
                    # For production, you'd want gettransaction + vin/vout matching
                    txs = rpc.rpc.listtransactions("*", 50)
                    for tx in txs:
                        if tx.get("address") == invoice.address and tx.get("amount", 0) > 0:
                            invoice.txid = tx.get("txid")
                            break
                    
                    db.commit()
                    logger.info(f"Invoice {invoice.id} marked as paid ({received} RTM)")
                    send_webhook(invoice, db)

            except Exception as e:
                logger.error(f"Polling error for invoice {invoice.id}: {e}")

        # Mark expired invoices
        expired = db.query(Invoice).filter(
            Invoice.status == "pending",
            Invoice.expires_at <= datetime.utcnow()
        ).update({"status": "expired"})
        if expired > 0:
            db.commit()
            logger.info(f"Marked {expired} invoices as expired")

    finally:
        db.close()


def start_polling_background_task():
    """Start the polling job"""
    scheduler.add_job(
        check_pending_invoices,
        trigger=IntervalTrigger(seconds=30),
        id='payment_polling',
        name='Poll pending RTM payments',
        replace_existing=True
    )
    logger.info("Payment polling background task started (every 30 seconds)")
    
    
def send_webhook(invoice, db):
    if not invoice.webhook_url:
        return
    
    payload = {
        "event": "payment.confirmed",
        "invoice_id": invoice.id,
        "amount_paid": invoice.amount_paid,
        "amount_requested": invoice.amount_requested,
        "address": invoice.address,
        "txid": invoice.txid,
        "paid_at": invoice.paid_at.isoformat(),
        "order_id": invoice.order_id,
        "merchant_id": invoice.merchant_id
    }

    try:
        # Fetch the merchant to get their secret API key
        merchant = db.query(Merchant).filter(Merchant.id == invoice.merchant_id).first()
        if not merchant:
            logger.error(f"Merchant {invoice.merchant_id} not found for webhook signature signing.")
            return

        # Prepare payload and compute signature
        payload_str = json.dumps(payload, sort_keys=True)
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{payload_str}".encode('utf-8')
        signature = hmac.new(
            merchant.api_key.encode('utf-8'),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-RTM-Signature": signature,
            "X-RTM-Timestamp": timestamp
        }

        response = requests.post(invoice.webhook_url, data=payload_str, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Webhook sent successfully to {invoice.webhook_url}")
    except Exception as e:
        logger.error(f"Webhook delivery failed for {invoice.id}: {e}")    