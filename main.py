"""
CROPIC Backend API — Full 17-Step Flow
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine as db_engine, get_db, Base
from models import User, Submission, Claim

from schemas import (
    LoginRequest,
    LoginResponse,
    UserOut,
    SubmissionCreate,
    SubmissionOut,
    ClaimCreate,
    ClaimReview,
    ClaimOut,
)

from auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    require_official,
)

from ai_engine import engine as ai_engine


# =====================================================
# DB INIT
# =====================================================

Base.metadata.create_all(bind=db_engine)


# =====================================================
# APP
# =====================================================

app = FastAPI(
    title="CROPIC API",
    description="PMFBY Crop Monitoring — Full Flow",
    version="2.0.0",
)


# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Change later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow()
    }


# =====================================================
# AUTH
# =====================================================

@app.post("/api/auth/register", response_model=UserOut)
def register(
    username: str,
    password: str,
    full_name: str,
    role: str = "farmer",
    district: Optional[str] = None,
    state: Optional[str] = None,
    aadhaar_id: Optional[str] = None,
    db: Session = Depends(get_db),
):

    existing_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        district=district,
        state=state,
        aadhaar_id=aadhaar_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@app.post("/api/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if not user or not verify_password(
        payload.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(user.id)

    return LoginResponse(
        token=token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# =====================================================
# SUBMISSION (AI FLOW)
# =====================================================

@app.post("/api/submit", response_model=SubmissionOut)
def submit_image(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    rejection_reason = None

    # GPS validation
    if payload.latitude and payload.longitude:
        if not (
            6.5 <= payload.latitude <= 37.1
            and
            68.1 <= payload.longitude <= 97.4
        ):
            rejection_reason = "Outside India"

    # Image validation
    if payload.image_base64 and len(payload.image_base64) < 500:
        rejection_reason = "Invalid image"

    ai_result = {}

    status = (
        "rejected"
        if rejection_reason
        else "assessed"
    )

    if not rejection_reason:
        ai_result = ai_engine.analyse(
            payload.image_base64,
            payload.growth_stage
        )

    damage = ai_result.get("damage_type", "none")

    prediction_label = (
        "healthy"
        if damage == "none"
        else "diseased"
    )

    sub = Submission(
        user_id=user.id,
        farmer_name=user.full_name,
        crop_type=payload.crop_type,
        growth_stage=payload.growth_stage,
        latitude=payload.latitude,
        longitude=payload.longitude,
        image_base64=payload.image_base64,
        status=status,
        rejection_reason=rejection_reason,
        prediction_label=prediction_label,
        damage_type=ai_result.get("damage_type"),
        severity_score=ai_result.get("severity_score"),
        yield_loss_pct=ai_result.get("yield_loss_pct"),
    )

    db.add(sub)
    db.commit()
    db.refresh(sub)

    return sub


@app.get("/api/submissions", response_model=list[SubmissionOut])
def list_submissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    return (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .all()
    )


# =====================================================
# CLAIMS
# =====================================================

@app.post("/api/claims", response_model=ClaimOut)
def create_claim(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    sub = (
        db.query(Submission)
        .filter(Submission.id == payload.submission_id)
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Submission not found"
        )

    claim = Claim(
        submission_id=sub.id,
        user_id=user.id,
        damage_description=payload.damage_description,
        estimated_loss_inr=payload.estimated_loss_inr,
        status="pending",
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    return claim


@app.get("/api/claims", response_model=list[ClaimOut])
def list_claims(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    return (
        db.query(Claim)
        .filter(Claim.user_id == user.id)
        .all()
    )


# =====================================================
# OFFICIAL REVIEW
# =====================================================

@app.post("/api/claims/{cid}/review", response_model=ClaimOut)
def review_claim(
    cid: int,
    payload: ClaimReview,
    db: Session = Depends(get_db),
    official: User = Depends(require_official),
):

    claim = (
        db.query(Claim)
        .filter(Claim.id == cid)
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    claim.status = (
        "approved"
        if payload.action == "approve"
        else "rejected"
    )

    claim.review_notes = payload.review_notes
    claim.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(claim)

    return claim


# =====================================================
# STATS
# =====================================================

@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):

    total = db.query(
        func.count(Submission.id)
    ).scalar()

    claims = db.query(
        func.count(Claim.id)
    ).scalar()

    return {
        "total_submissions": total,
        "total_claims": claims,
    }