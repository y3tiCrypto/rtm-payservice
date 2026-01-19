from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import uuid
import secrets

from app.database import get_db
from app.models import Merchant

router = APIRouter()

class MerchantCreate(BaseModel):
    email: EmailStr

@router.post("/create")
def create_merchant(merchant_data: MerchantCreate, db: Session = Depends(get_db)):
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