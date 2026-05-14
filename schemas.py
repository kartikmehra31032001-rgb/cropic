from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user_id: int
    full_name: str
    role: str

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    district: Optional[str]
    state: Optional[str]
    class Config:
        from_attributes = True


# ── Submissions ───────────────────────────────────────────────────────────────

class SubmissionCreate(BaseModel):
    plot_id: Optional[str] = None
    district: str
    state: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    growth_stage: str
    crop_type: str
    notes: Optional[str] = None
    image_base64: Optional[str] = None
    image_filename: Optional[str] = None

class SubmissionOut(BaseModel):
    id: int
    user_id: int
    farmer_name: Optional[str]
    plot_id: Optional[str]
    district: Optional[str]
    state: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    growth_stage: Optional[str]
    crop_type: Optional[str]
    notes: Optional[str]
    prediction_label: Optional[str]
    disease_type: Optional[str]
    crop_detected: Optional[str]
    damage_type: Optional[str]
    severity_score: Optional[float]
    yield_loss_pct: Optional[float]
    status: str
    rejection_reason: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ── Claims ────────────────────────────────────────────────────────────────────

class ClaimCreate(BaseModel):
    submission_id: int
    damage_description: str
    claimed_damage_type: Optional[str] = None
    affected_area_acres: Optional[float] = None
    estimated_loss_inr: Optional[float] = None

class ClaimReview(BaseModel):
    action: str          # approve | reject
    review_notes: Optional[str] = None

class ClaimOut(BaseModel):
    id: int
    submission_id: int
    user_id: int
    damage_description: str
    claimed_damage_type: Optional[str]
    affected_area_acres: Optional[float]
    estimated_loss_inr: Optional[float]
    status: str
    reviewer_name: Optional[str]
    review_notes: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True


# ── Stats ─────────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total_submissions: int
    assessed: int
    pending: int
    rejected: int
    total_claims: int
    claims_pending: int
    claims_approved: int
    claims_rejected: int
    avg_severity: Optional[float]
    avg_yield_loss: Optional[float]
    damage_breakdown: dict
    district_breakdown: list
