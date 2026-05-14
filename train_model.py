from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, Subset
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

# ---------------- CONFIG ----------------
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "plantvillage_data" / "color"
SAVE_PATH = ROOT_DIR / "plantvillage_efficientnet.pth"

EPOCHS = 3
BATCH_SIZE = 64
LR = 1e-4
VAL_SPLIT = 0.2
NUM_CLASSES = 38
NUM_WORKERS = 0  # Windows-safe; avoids multiprocessing spawn errors


def build_datasets():
    """Create train/val subsets with separate transforms."""
    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    val_tf = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    base_ds = datasets.ImageFolder(DATA_DIR)
    n_val = int(len(base_ds) * VAL_SPLIT)
    n_train = len(base_ds) - n_val

    # Deterministic split so every run is identical
    generator = torch.Generator().manual_seed(42)
    train_subset, val_subset = random_split(base_ds, [n_train, n_val], generator=generator)

    train_ds = Subset(
        datasets.ImageFolder(DATA_DIR, transform=train_tf),
        train_subset.indices,
    )
    val_ds = Subset(
        datasets.ImageFolder(DATA_DIR, transform=val_tf),
        val_subset.indices,
    )

    return train_ds, val_ds


# ---------------- MAIN ----------------
if __name__ == "__main__":
    assert DATA_DIR.exists(), f"Dataset folder not found: {DATA_DIR}"

    train_ds, val_ds = build_datasets()

    print(f"Classes: {len(train_ds.dataset.classes)}")
    print(f"Train images: {len(train_ds)} | Val images: {len(val_ds)}")

    # DataLoaders (Windows-safe)
    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=False,
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=False,
    )

    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Model
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, NUM_CLASSES)
    model = model.to(device)

    # Loss + Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=4, gamma=0.3)

    best_val_acc = 0.0

    # ---------------- TRAIN LOOP ----------------
    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_correct = 0
        train_total = 0

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            preds = outputs.argmax(1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

        # ---------------- VALIDATION ----------------
        model.eval()
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)

                preds = outputs.argmax(1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        train_acc = train_correct / train_total
        val_acc = val_correct / val_total

        print(f"Epoch {epoch:02d}/{EPOCHS} "
              f"train_acc={train_acc:.3f} val_acc={val_acc:.3f}")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  Saved best model ({val_acc:.3f})")

        scheduler.step()

    print("\nTraining complete!")
    print(f"Best validation accuracy: {best_val_acc:.3f}")
    print(f"Model saved at: {SAVE_PATH}")
