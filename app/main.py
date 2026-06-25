from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import asyncio
from contextlib import asynccontextmanager

from app.database import engine, Base, get_db
from app.config import settings
from app.routers import payment, merchant
from app.services import polling
from app.services.polling import start_polling_background_task
from app.services.zmq_listener import start_zmq_background_listener
from app.logging_config import setup_logging

setup_logging()

import logging
logger = logging.getLogger("app.main")

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RaptoreumPay starting...")
    logger.info(f"RPC connection: {settings.rpc_host}:{settings.rpc_port}")
    
    # 1. Capture main event loop for WebSockets
    loop = asyncio.get_running_loop()
    polling.main_loop = loop
    
    # 2. Start background ZMQ thread if enabled
    start_zmq_background_listener(loop)
    
    # 3. Start background polling task (runs alongside ZMQ as backup / fallback)
    start_polling_background_task()
    
    # 4. Start Redis pub/sub socket listener (horizontal scaling)
    from app.routers.payment import manager
    manager.start_redis_listener(loop)
    
    yield

# Create all tables (Managed by Alembic migrations)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RaptoreumPay",
    description="Simple non-custodial RTM payment processor",
    version="1.7.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow CORS for widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (widget.js, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(payment.router, prefix="/api/payment", tags=["payments"])
app.include_router(merchant.router, prefix="/api/merchant", tags=["merchants"])

# Very basic admin protection
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = credentials.username == settings.admin_username
    correct_password = credentials.password == settings.admin_password
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/admin/backup")
def admin_backup(db: Session = Depends(get_db), _=Depends(verify_admin)):
    # Very simple MVP backup - return list of recent invoices
    # In real version → export CSV/JSON
    from app.models import Invoice
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(100).all()
    
    return {
        "status": "ok",
        "message": "Admin backup view (MVP) - showing last 100 invoices",
        "invoices": [
            {
                "id": inv.id,
                "merchant_id": inv.merchant_id,
                "address": inv.address,
                "amount_requested": inv.amount_requested,
                "status": inv.status,
                "created_at": inv.created_at.isoformat()
            } for inv in invoices
        ]
    }



@app.get("/")
def read_root():
    return {
        "message": "RaptoreumPay MVP API is running",
        "docs": "/docs",
        "widget_example": "See /static/widget.js for embed instructions"
    }

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    from app.rpc_client import rpc
    
    health_status = {
        "status": "healthy",
        "database": "untested",
        "redis": "disabled",
        "rpc": "untested"
    }
    
    # 1. Test Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 2. Test Redis if enabled
    if settings.redis_enabled:
        from app.redis_client import redis_client
        if redis_client is not None:
            try:
                redis_client.ping()
                health_status["redis"] = "healthy"
            except Exception as e:
                health_status["redis"] = f"unhealthy: {str(e)}"
                health_status["status"] = "unhealthy"
        else:
            health_status["redis"] = "unhealthy: client not initialized"
            health_status["status"] = "unhealthy"

    # 3. Test RPC Node
    try:
        rpc.rpc.getblockchaininfo()
        health_status["rpc"] = "healthy"
    except Exception as e:
        health_status["rpc"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Determine response status
    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)