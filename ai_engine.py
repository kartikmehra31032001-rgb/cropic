import io, base64, random
from typing import Optional
from pathlib import Path

from PIL import Image

# ================= CONFIG =================
NUM_CLASSES = 38
WEIGHTS_PATH = Path(__file__).parent / "plant_model.pth"   # 👈 your file name

# ================= CLASSES =================
PLANTVILLAGE_CLASSES = [
    "Apple___Apple_scab","Apple___Black_rot","Apple___Cedar_apple_rust","Apple___healthy",
    "Blueberry___healthy","Cherry___Powdery_mildew","Cherry___healthy",
    "Corn___Cercospora_leaf_spot","Corn___Common_rust","Corn___Northern_Leaf_Blight","Corn___healthy",
    "Grape___Black_rot","Grape___Esca_Black_Measles","Grape___Leaf_blight","Grape___healthy",
    "Orange___Haunglongbing","Peach___Bacterial_spot","Peach___healthy",
    "Pepper___Bacterial_spot","Pepper___healthy",
    "Potato___Early_blight","Potato___Late_blight","Potato___healthy",
    "Raspberry___healthy",
    "Rice___Brown_spot","Rice___Leaf_scald","Rice___Neck_blast","Rice___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch","Strawberry___healthy",
    "Tomato___Bacterial_spot","Tomato___Early_blight","Tomato___Late_blight","Tomato___Leaf_Mold","Tomato___healthy",
    "Wheat___Yellow_rust"
]

# ================= HELPERS =================
def _class_to_crop(label):
    return label.split("___")[0].lower()

def _class_to_damage(label):
    l = label.lower()
    if "healthy" in l: return "none"
    if "rust" in l or "blight" in l: return "fungal_disease"
    if "bacterial" in l or "spot" in l: return "pest_attack"
    if "mildew" in l or "mold" in l: return "fungal_disease"
    return "fungal_disease"

def _to_yield(severity, stage):
    mult = {"sowing":0.5,"vegetative":0.7,"flowering":1.0,"maturity":0.9}.get(stage,0.75)
    return min(100.0, severity * mult * 0.85)

# ================= ENGINE =================
class CROPICEngine:
    def __init__(self):
        self.torch = None
        self.nn = None
        self.T = None
        self.efficientnet_b0 = None
        self.model = None
        self.transform = None
        self.loaded = False
        self.load_error = None

        if self._load_torch():
            self._build_model()
            self._load_weights()

    def _load_torch(self):
        try:
            import torch
            import torch.nn as nn
            import torchvision.transforms as T
            from torchvision.models import efficientnet_b0
        except Exception as e:
            self.load_error = e
            print("AI engine running in simulation mode. PyTorch could not be loaded:", e)
            return False

        self.torch = torch
        self.nn = nn
        self.T = T
        self.efficientnet_b0 = efficientnet_b0
        return True

    def _build_model(self):
        self.model = self.efficientnet_b0(weights=None)  # no pretrained (safe)
        in_features = self.model.classifier[1].in_features
        self.model.classifier[1] = self.nn.Linear(in_features, NUM_CLASSES)
        self.model.eval()

        self.transform = self.T.Compose([
            self.T.Resize((224,224)),
            self.T.ToTensor()
        ])

    def _load_weights(self):
        if not WEIGHTS_PATH.exists():
            print("❌ Model file not found → Simulation mode")
            return

        try:
            state = self.torch.load(WEIGHTS_PATH, map_location="cpu")

            # Handle both cases
            if isinstance(state, dict):
                self.model.load_state_dict(state)
            else:
                self.model = state

            self.model.eval()
            self.loaded = True
            print("✅ Model loaded successfully")

        except Exception as e:
            print("❌ Error loading model:", e)
            self.loaded = False

    # ================= MAIN FUNCTION =================
    def analyse(self, image_base64: Optional[str], growth_stage: str):
        if self.loaded and image_base64:
            return self._real(image_base64, growth_stage)
        return self._fake(growth_stage)

    # ================= REAL =================
    def _real(self, image_base64, growth_stage):
        try:
            img_bytes = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            x = self.transform(img).unsqueeze(0)

            with self.torch.no_grad():
                out = self.model(x)
                probs = self.torch.softmax(out, dim=1)[0]

            idx = int(probs.argmax())
            conf = float(probs[idx])

            label = PLANTVILLAGE_CLASSES[idx]
            crop = _class_to_crop(label)
            damage = _class_to_damage(label)

            severity = round(random.uniform(30, 80), 1)
            yield_loss = round(_to_yield(severity, growth_stage), 1)

            return {
                "class": label,
                "crop_detected": crop,
                "crop_confidence": round(conf, 3),
                "damage_type": damage,
                "damage_confidence": round(conf, 3),
                "severity_score": severity,
                "yield_loss_pct": yield_loss,
                "mode": "real"
            }

        except Exception as e:
            print("Inference error:", e)
            return self._fake(growth_stage)

    # ================= SIMULATION =================
    def _fake(self, growth_stage):
        label = random.choice(PLANTVILLAGE_CLASSES)
        crop = _class_to_crop(label)
        damage = _class_to_damage(label)

        severity = round(random.uniform(30, 80), 1)
        yield_loss = round(_to_yield(severity, growth_stage), 1)

        return {
            "class": label,
            "crop_detected": crop,
            "crop_confidence": round(random.uniform(0.7, 0.95), 3),
            "damage_type": damage,
            "damage_confidence": round(random.uniform(0.7, 0.95), 3),
            "severity_score": severity,
            "yield_loss_pct": yield_loss,
            "mode": "simulation"
        }

# ================= INSTANCE =================
engine = CROPICEngine()
