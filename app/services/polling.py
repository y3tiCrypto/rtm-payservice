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
import asyncio
import uuid
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import Invoice, Merchant, WebhookDelivery
from app.rpc_client import rpc
from app.routers.payment import manager
from app.config import settings

main_loop = None

def trigger_ws_broadcast(invoice_id: str, status: str):
    if main_loop is not None:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast_status(invoice_id, status),
            main_loop
        )

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.start()


def check_pending_invoices():
    """Background task: poll pending (0-conf) and detected (minconf) invoices"""
    db = SessionLocal()
    try:
        # 1. Fetch pending invoices (not yet seen in mempool)
        pending = db.query(Invoice).filter(
            Invoice.status == "pending",
            Invoice.expires_at > datetime.utcnow()
        ).all()

        for invoice in pending:
            try:
                received = rpc.get_received_by_address(invoice.address, minconf=0)
                if received >= invoice.amount_requested * 0.98:
                    # Retrieve transaction ID
                    txs = rpc.rpc.listtransactions("*", 50)
                    txid = None
                    for tx in txs:
                        if tx.get("address") == invoice.address and tx.get("amount", 0) > 0:
                            txid = tx.get("txid")
                            break
                    
                    if settings.min_confirmations == 0:
                        invoice.status = "paid"
                        invoice.amount_paid = received
                        invoice.paid_at = datetime.utcnow()
                        invoice.txid = txid
                        db.commit()
                        logger.info(f"Invoice {invoice.id} marked as paid (0-conf target met)")
                        queue_webhook_delivery(invoice, db)
                        trigger_ws_broadcast(invoice.id, "paid")
                    else:
                        invoice.status = "detected"
                        invoice.amount_paid = received
                        invoice.txid = txid
                        db.commit()
                        logger.info(f"Invoice {invoice.id} marked as detected (awaiting confirmation)")
                        trigger_ws_broadcast(invoice.id, "detected")
            except Exception as e:
                logger.error(f"Polling check error for pending invoice {invoice.id}: {e}")

        # 2. Fetch detected invoices (seen in mempool, waiting for block confirmations)
        detected = db.query(Invoice).filter(
            Invoice.status == "detected",
            Invoice.expires_at > datetime.utcnow()
        ).all()

        for invoice in detected:
            try:
                # Query with target confirmations depth
                received = rpc.get_received_by_address(invoice.address, minconf=settings.min_confirmations)
                if received >= invoice.amount_requested * 0.98:
                    invoice.status = "paid"
                    invoice.amount_paid = received
                    invoice.paid_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Invoice {invoice.id} confirmed paid at depth {settings.min_confirmations}")
                    queue_webhook_delivery(invoice, db)
                    trigger_ws_broadcast(invoice.id, "paid")
            except Exception as e:
                logger.error(f"Polling check error for detected invoice {invoice.id}: {e}")

        # Mark expired invoices
        expired_records = db.query(Invoice).filter(
            Invoice.status.in_(["pending", "detected"]),
            Invoice.expires_at <= datetime.utcnow()
        ).all()
        for exp_inv in expired_records:
            exp_inv.status = "expired"
            db.commit()
            logger.info(f"Invoice {exp_inv.id} marked as expired")
            trigger_ws_broadcast(exp_inv.id, "expired")

    finally:
        db.close()


def queue_webhook_delivery(invoice, db):
    """Saves a pending WebhookDelivery record to the database"""
    if not invoice.webhook_url:
        return
    
    payload = {
        "event": "payment.confirmed",
        "invoice_id": invoice.id,
        "amount_paid": invoice.amount_paid,
        "amount_requested": invoice.amount_requested,
        "address": invoice.address,
        "txid": invoice.txid,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "order_id": invoice.order_id,
        "merchant_id": invoice.merchant_id
    }

    try:
        merchant = db.query(Merchant).filter(Merchant.id == invoice.merchant_id).first()
        if not merchant:
            logger.error(f"Merchant {invoice.merchant_id} not found for webhook signing.")
            return

        payload_str = json.dumps(payload, sort_keys=True)
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{payload_str}".encode('utf-8')
        signature = hmac.new(
            merchant.api_key.encode('utf-8'),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        delivery_payload = {
            "payload": payload_str,
            "signature": signature,
            "timestamp": timestamp
        }

        new_delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            url=invoice.webhook_url,
            payload=json.dumps(delivery_payload),
            status="pending",
            attempts=0
        )
        db.add(new_delivery)
        db.commit()
        logger.info(f"Webhook delivery queued for invoice {invoice.id}")
    except Exception as e:
        logger.error(f"Failed to queue webhook for invoice {invoice.id}: {e}")


def process_webhook_deliveries():
    """Background task: processes pending/failed webhooks in the DB queue with exponential backoff"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Fetch deliveries that are 'pending' or 'failed' (and ready for retry)
        deliveries = db.query(WebhookDelivery).filter(
            or_(
                WebhookDelivery.status == "pending",
                (WebhookDelivery.status == "failed") & (WebhookDelivery.next_attempt_at <= now)
            )
        ).limit(50).all()

        for delivery in deliveries:
            try:
                delivery_data = json.loads(delivery.payload)
                payload_str = delivery_data["payload"]
                signature = delivery_data["signature"]
                timestamp = delivery_data["timestamp"]

                headers = {
                    "Content-Type": "application/json",
                    "X-RTM-Signature": signature,
                    "X-RTM-Timestamp": timestamp
                }

                delivery.attempts += 1
                response = requests.post(delivery.url, data=payload_str, headers=headers, timeout=10)
                response.raise_for_status()

                # Success
                delivery.status = "sent"
                delivery.last_error = None
                db.commit()
                logger.info(f"Webhook delivery {delivery.id} sent successfully on attempt {delivery.attempts}")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Webhook delivery {delivery.id} failed (attempt {delivery.attempts}): {error_msg}")
                
                if delivery.attempts >= 5:
                    delivery.status = "dlq"
                    delivery.next_attempt_at = None
                else:
                    delivery.status = "failed"
                    # Exponential backoff: retry in 2, 4, 8, 16 minutes
                    delay_minutes = 2 ** delivery.attempts
                    delivery.next_attempt_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
                
                delivery.last_error = error_msg
                db.commit()
    except Exception as e:
        logger.error(f"Error processing webhook deliveries queue: {e}")
    finally:
        db.close()


def start_polling_background_task():
    """Start background jobs"""
    # 1. Invoice Polling Job (every 30 seconds)
    scheduler.add_job(
        check_pending_invoices,
        trigger=IntervalTrigger(seconds=30),
        id='payment_polling',
        name='Poll pending RTM payments',
        replace_existing=True
    )
    
    # 2. Webhook Processor Job (every 30 seconds)
    scheduler.add_job(
        process_webhook_deliveries,
        trigger=IntervalTrigger(seconds=30),
        id='webhook_queue_processing',
        name='Process webhook queue',
        replace_existing=True
    )
    logger.info("Payment polling and webhook queue background tasks started.")