import time
import zmq
import logging
import asyncio
import threading
from datetime import datetime
from app.config import settings
from app.rpc_client import rpc
from app.database import SessionLocal
from app.models import Invoice, Merchant
from app.services import polling

logger = logging.getLogger(__name__)

# Shared reference to the main event loop for WS broadcasts
main_loop = None

def zmq_listener_loop():
    """
    Subscribes to the Raptoreum Core Node ZMQ 'hashtx' stream.
    Receives unconfirmed transaction hashes immediately upon broadcast.
    """
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    
    zmq_url = f"tcp://{settings.zmq_host}:{settings.zmq_port}"
    try:
        socket.connect(zmq_url)
        socket.setsockopt_string(zmq.SUBSCRIBE, "hashtx")
        logger.info(f"ZeroMQ: Subscribed to 'hashtx' events at {zmq_url}")
    except Exception as e:
        logger.error(f"ZeroMQ: Failed to connect to ZMQ publisher: {e}")
        return

    while True:
        try:
            # hashtx sends multi-part message: [topic, tx_hash_bytes, sequence_bytes]
            topic, body, seq = socket.recv_multipart()
            txid = body.hex()
            
            # Spin up a worker thread to fetch and inspect details without blocking ZMQ stream
            threading.Thread(target=process_blockchain_transaction, args=(txid,), daemon=True).start()
        except Exception as e:
            logger.error(f"ZeroMQ: Error in listener socket loop: {e}")
            time.sleep(1)

def process_blockchain_transaction(txid: str):
    """
    Retrieves transaction details from Core node and validates it against pending invoices.
    """
    tx_info = rpc.get_transaction(txid)
    if not tx_info:
        return
        
    details = tx_info.get("details", [])
    db = SessionLocal()
    try:
        for detail in details:
            # We are only interested in incoming txs (category="receive")
            if detail.get("category") == "receive":
                address = detail.get("address")
                amount = float(detail.get("amount", 0))
                
                # Check if this address matches an active pending invoice in our DB
                invoice = db.query(Invoice).filter(
                    Invoice.address == address,
                    Invoice.status == "pending",
                    Invoice.expires_at > datetime.utcnow()
                ).first()
                
                if invoice:
                    logger.info(f"ZeroMQ: Detected pending invoice address match for {address}. Confirming RTM amount...")
                    # Fetch total received at address to cover multi-output payments
                    received = rpc.get_received_by_address(address, minconf=0)
                    
                    if received >= invoice.amount_requested * 0.98:
                        from app.services.polling import queue_webhook_delivery
                        
                        if settings.min_confirmations == 0:
                            invoice.status = "paid"
                            invoice.amount_paid = received
                            invoice.paid_at = datetime.utcnow()
                            invoice.txid = txid
                            db.commit()
                            logger.info(f"ZeroMQ: Invoice {invoice.id} successfully marked as paid (0-conf)")
                            queue_webhook_delivery(invoice, db)
                            status_to_broadcast = "paid"
                        else:
                            invoice.status = "detected"
                            invoice.amount_paid = received
                            invoice.txid = txid
                            db.commit()
                            logger.info(f"ZeroMQ: Invoice {invoice.id} marked as detected (awaiting confirmation)")
                            status_to_broadcast = "detected"
                        
                        # Dispatch WebSocket broadcast to the client
                        if main_loop is not None:
                            from app.routers.payment import manager
                            asyncio.run_coroutine_threadsafe(
                                manager.broadcast_status(invoice.id, status_to_broadcast),
                                main_loop
                            )
    except Exception as e:
        logger.error(f"ZeroMQ: Error processing transaction {txid}: {e}")
    finally:
        db.close()

def start_zmq_background_listener(loop):
    """
    Spawns the ZMQ listener thread as a background daemon.
    """
    global main_loop
    main_loop = loop
    
    if not settings.zmq_enabled:
        logger.info("ZeroMQ: Daemon listener disabled by configuration.")
        return
        
    listener_thread = threading.Thread(target=zmq_listener_loop, name="ZMQListenerThread", daemon=True)
    listener_thread.start()
    logger.info("ZeroMQ: Background event streaming thread launched.")
