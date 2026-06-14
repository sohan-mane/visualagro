"""
auth.py — JWT creation / verification + password hashing
Uses python-jose (HS256) and passlib (bcrypt).
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Vendor
from schemas import TokenData

SECRET_KEY  = os.getenv("SECRET_KEY", "change-me-in-production-use-32-char-secret")
ALGORITHM   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))  # 24 h

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


import bcrypt

# ── Password helpers ─────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# ── Token helpers ────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── FastAPI dependency — current authenticated vendor ────────────────

def get_current_vendor(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> Vendor:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload    = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        vendor_id: int = payload.get("sub")
        if vendor_id is None:
            raise credentials_exc
        token_data = TokenData(vendor_id=int(vendor_id))
    except JWTError:
        raise credentials_exc

    vendor = db.get(Vendor, token_data.vendor_id)
    if vendor is None or not vendor.is_active:
        raise credentials_exc
    return vendor
