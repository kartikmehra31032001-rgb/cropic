from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from database import Base


class User(Base):
    """Farmer or official account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="farmer")  # farmer | official
    aadhaar_id = Column(String(20))
    district = Column(String(80))
    state = Column(String(80))
    created_at = Column(DateTime, default=datetime.utcnow)


class Submission(Base):
    """One crop image + AI prediction from a farmer."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    farmer_name = Column(String(120))
    plot_id = Column(String(50))
    district = Column(String(80), index=True)
    state = Column(String(80))
    latitude = Column(Float)
    longitude = Column(Float)
    captured_at = Column(DateTime, default=datetime.utcnow)
    growth_stage = Column(String(50))
    crop_type = Column(String(80))
    notes = Column(Text)
    image_filename = Column(String(255))
    image_base64 = Column(Text)
    prediction_label = Column(String(40))   # healthy | diseased
    disease_type = Column(String(80))
    crop_detected = Column(String(80))
    crop_confidence = Column(Float)
    damage_type = Column(String(80))
    damage_confidence = Column(Float)
    severity_score = Column(Float)
    yield_loss_pct = Column(Float)
    ai_raw_output = Column(JSON)
    status = Column(String(30), default="pending")
    rejection_reason = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Claim(Base):
    """Insurance claim raised by a farmer against a submission."""
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    damage_description = Column(Text, nullable=False)
    claimed_damage_type = Column(String(80))
    affected_area_acres = Column(Float)
    estimated_loss_inr = Column(Float)
    status = Column(String(20), default="pending")  # pending | approved | rejected
    reviewed_by_id = Column(Integer, ForeignKey("users.id"))
    reviewer_name = Column(String(120))
    review_notes = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
