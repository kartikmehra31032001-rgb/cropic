from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
import hashlib

security = HTTPBearer()

# ---------------- PASSWORD ----------------
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str):
    return hash_password(password) == hashed

# ---------------- TOKEN ----------------
def create_token(user_id: int):
    # simple token (you already use this style)
    return hashlib.sha256(f"user-{user_id}".encode()).hexdigest()

def get_user_from_token(token: str, db: Session):
    # simple logic: match token with user
    users = db.query(User).all()
    for user in users:
        if create_token(user.id) == token:
            return user
    return None

# ---------------- AUTH DEPENDENCY ----------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials  # removes "Bearer "

    user = get_user_from_token(token, db)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user


# ---------------- ROLE CHECK ----------------
def require_official(user: User = Depends(get_current_user)):
    if user.role != "official":
        raise HTTPException(status_code=403, detail="Only officials allowed")
    return user
