from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn

from app.database import engine, Base, get_db
from app.config import settings
from app.routers import payment, merchant
from app.services.polling import start_polling_background_task

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RaptoreumPay MVP",
    description="Simple non-custodial RTM payment processor",
    version="0.1.0"
)

# Allow CORS for widget (you can restrict origins later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← tighten in production!
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

@app.on_event("startup")
async def startup_event():
    print("RaptoreumPay MVP starting...")
    print(f"RPC connection: {settings.rpc_host}:{settings.rpc_port}")
    # Start background polling task
    start_polling_background_task()

@app.get("/")
def read_root():
    return {
        "message": "RaptoreumPay MVP API is running",
        "docs": "/docs",
        "widget_example": "See /static/widget.js for embed instructions"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)