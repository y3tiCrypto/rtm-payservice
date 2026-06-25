from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models import Invoice, Merchant
from app.rpc_client import rpc
from app.services.price import get_rtm_price_usd
from app.config import settings
from app.limiter import limiter

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
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def create_invoice(
    request: Request,
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
        if merchant.xpub:
            from app.services.hd_wallet import derive_rtm_address
            address = derive_rtm_address(merchant.xpub, merchant.next_address_index)
            merchant.next_address_index += 1
        else:
            address = rpc.get_new_address(label=f"invoice-{uuid.uuid4().hex[:8]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Address generation failed: {str(e)}")

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


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.loop = None
        self.redis_thread = None

    def start_redis_listener(self, loop):
        from app.redis_client import redis_client
        import json
        import threading
        
        self.loop = loop
        if redis_client is None:
            return

        def redis_pubsub_worker():
            pubsub = redis_client.pubsub()
            pubsub.subscribe("raptoreumpay:invoice_updates")
            for message in pubsub.listen():
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        invoice_id = data.get("invoice_id")
                        status = data.get("status")
                        if invoice_id and status:
                            asyncio.run_coroutine_threadsafe(
                                self.local_broadcast_status(invoice_id, status),
                                self.loop
                            )
                    except Exception:
                        pass

        self.redis_thread = threading.Thread(target=redis_pubsub_worker, daemon=True)
        self.redis_thread.start()

    async def connect(self, websocket: WebSocket, invoice_id: str):
        await websocket.accept()
        if invoice_id not in self.active_connections:
            self.active_connections[invoice_id] = []
        self.active_connections[invoice_id].append(websocket)

    def disconnect(self, websocket: WebSocket, invoice_id: str):
        if invoice_id in self.active_connections:
            self.active_connections[invoice_id].remove(websocket)
            if not self.active_connections[invoice_id]:
                del self.active_connections[invoice_id]

    async def local_broadcast_status(self, invoice_id: str, status: str):
        if invoice_id in self.active_connections:
            for connection in self.active_connections[invoice_id]:
                try:
                    await connection.send_json({"invoice_id": invoice_id, "status": status})
                except Exception:
                    pass

    async def broadcast_status(self, invoice_id: str, status: str):
        from app.redis_client import redis_client
        import json

        if redis_client is not None:
            try:
                payload = json.dumps({"invoice_id": invoice_id, "status": status})
                redis_client.publish("raptoreumpay:invoice_updates", payload)
                return
            except Exception:
                pass
        
        await self.local_broadcast_status(invoice_id, status)

manager = ConnectionManager()


@router.websocket("/{invoice_id}/ws")
async def websocket_endpoint(websocket: WebSocket, invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, invoice_id)
    try:
        # Send initial status
        await websocket.send_json({"invoice_id": invoice_id, "status": invoice.status})
        while True:
            # Keep socket connection open for lifecycle broadcasts
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, invoice_id)