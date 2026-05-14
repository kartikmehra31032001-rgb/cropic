"""
Creates tables and seeds demo users + 60 submissions + 20 claims.
Run once:  python init_db.py
"""
import random
from datetime import datetime, timedelta
from database import engine, SessionLocal, Base
from models import User, Submission, Claim
from auth import hash_password

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Demo users ────────────────────────────────────────────────────────────────
FARMERS = [
    ("ramesh_k",   "pass123", "Ramesh Kumar",   "Vidarbha",  "Maharashtra"),
    ("sunita_d",   "pass123", "Sunita Devi",    "Ludhiana",  "Punjab"),
    ("pradeep_s",  "pass123", "Pradeep Singh",  "Kurnool",   "Andhra Pradesh"),
    ("meena_b",    "pass123", "Meena Bai",      "Barmer",    "Rajasthan"),
    ("arjun_p",    "pass123", "Arjun Patel",    "Guntur",    "Andhra Pradesh"),
]
OFFICIALS = [
    ("officer_mh", "admin123", "Deepak Sharma",  "Vidarbha",  "Maharashtra"),
    ("officer_pb", "admin123", "Gurpreet Kaur",  "Ludhiana",  "Punjab"),
]

farmer_objs = []
for un, pw, name, dist, state in FARMERS:
    u = User(username=un, password_hash=hash_password(pw), full_name=name,
             role="farmer", district=dist, state=state, aadhaar_id=f"XXXX{random.randint(1000,9999)}")
    db.add(u); farmer_objs.append((u, dist, state))

for un, pw, name, dist, state in OFFICIALS:
    db.add(User(username=un, password_hash=hash_password(pw), full_name=name,
                role="official", district=dist, state=state))
db.commit()
for fo in farmer_objs:
    db.refresh(fo[0])

# ── Seed submissions ──────────────────────────────────────────────────────────
DISTRICT_COORDS = {
    "Vidarbha": (20.5, 78.1), "Ludhiana": (30.9, 75.8),
    "Kurnool": (15.8, 78.0), "Barmer": (25.7, 71.4), "Guntur": (16.3, 80.4),
}
DAMAGE_TYPES = ["none","lodging","flood_inundation","water_stress","pest_attack","fungal_disease"]
DAMAGE_SEV   = {"none":(0,5),"lodging":(25,55),"flood_inundation":(55,85),
                "water_stress":(30,60),"pest_attack":(35,70),"fungal_disease":(40,75)}
STAGES = ["sowing","vegetative","flowering","maturity"]
CROPS  = ["Wheat","Rice","Cotton","Maize","Soybean","Groundnut"]

submissions_created = []
for farmer_obj, dist, state in farmer_objs:
    lat0, lng0 = DISTRICT_COORDS.get(dist, (20.0, 78.0))
    for _ in range(12):
        damage = random.choices(DAMAGE_TYPES, weights=[0.28,0.12,0.18,0.14,0.14,0.14])[0]
        s_min, s_max = DAMAGE_SEV[damage]
        sev = round(random.uniform(s_min, s_max), 1)
        stage = random.choice(STAGES)
        sm = {"sowing":0.5,"vegetative":0.7,"flowering":1.0,"maturity":0.9}[stage]
        crop = random.choice(CROPS)
        days_ago = random.randint(0, 25)
        ts = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0,23))
        pred = "healthy" if damage == "none" else "diseased"
        dis  = None if damage == "none" else damage.replace("_"," ").title()

        sub = Submission(
            user_id=farmer_obj.id, farmer_name=farmer_obj.full_name,
            plot_id=f"PLOT{random.randint(1000,9999)}", district=dist, state=state,
            latitude=round(lat0+random.uniform(-0.5,0.5),5),
            longitude=round(lng0+random.uniform(-0.5,0.5),5),
            growth_stage=stage, crop_type=crop,
            notes=random.choice([None,"Heavy rain last week","Yellowing observed","Leaves curling",None]),
            status="assessed",
            prediction_label=pred, disease_type=dis,
            crop_detected=crop.lower(), damage_type=damage,
            crop_confidence=round(random.uniform(0.72,0.97),3),
            damage_confidence=round(random.uniform(0.60,0.95),3),
            severity_score=sev,
            yield_loss_pct=round(min(100,sev*sm*0.85),1),
            ai_raw_output={"inference_mode":"seed","model":"efficientnet_b0"},
            created_at=ts, updated_at=ts, captured_at=ts,
        )
        db.add(sub)
        submissions_created.append((sub, farmer_obj))

db.commit()
for sub, _ in submissions_created:
    db.refresh(sub)

# ── Seed claims ───────────────────────────────────────────────────────────────
diseased_subs = [(s, f) for s, f in submissions_created if s.prediction_label == "diseased"]
random.shuffle(diseased_subs)
statuses = ["pending","approved","rejected","pending","pending"]
for i, (sub, farmer) in enumerate(diseased_subs[:20]):
    cstatus = statuses[i % len(statuses)]
    ts = sub.created_at + timedelta(hours=random.randint(2,48))
    claim = Claim(
        submission_id=sub.id, user_id=farmer.id,
        damage_description=random.choice([
            "Significant crop damage due to flood inundation in lower field section.",
            "Pest attack observed on leaves — yield severely affected.",
            "Water stress for 10+ days caused extensive wilting and loss.",
            "Lodging due to heavy winds — over 40% of crop flattened.",
            "Fungal disease spreading rapidly — spraying has not helped.",
        ]),
        claimed_damage_type=sub.damage_type,
        affected_area_acres=round(random.uniform(0.5, 5.0), 1),
        estimated_loss_inr=round(random.uniform(5000, 80000), -2),
        status=cstatus,
        reviewer_name="Deepak Sharma" if cstatus != "pending" else None,
        review_notes="Verified via field visit and satellite data." if cstatus == "approved"
                     else ("Insufficient evidence of damage." if cstatus == "rejected" else None),
        reviewed_at=ts + timedelta(days=2) if cstatus != "pending" else None,
        created_at=ts, updated_at=ts,
    )
    db.add(claim)

db.commit()
db.close()

print("✓ DB seeded: 5 farmers, 2 officials, 60 submissions, 20 claims")
print()
print("Demo logins:")
print("  Farmer  →  ramesh_k  / pass123")
print("  Farmer  →  sunita_d  / pass123")
print("  Official→  officer_mh / admin123")
