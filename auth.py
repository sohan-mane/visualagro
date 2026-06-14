"""
routers/auth.py — /auth  (register · login)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models   import Vendor
from schemas  import VendorCreate, VendorOut, Token
from auth     import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=VendorOut, status_code=201,
             summary="Register a new vendor account")
def register(payload: VendorCreate, db: Session = Depends(get_db)):
    if db.query(Vendor).filter(Vendor.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    vendor = Vendor(
        name=payload.name,
        market=payload.market,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.post("/login", response_model=Token,
             summary="Login and receive a JWT access token")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.email == form.username).first()
    if not vendor or not verify_password(form.password, vendor.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": str(vendor.id)})
    return {"access_token": token, "token_type": "bearer"}
