"""
Train an image classifier to recognize OSRS objects, NPCs, items.
Uses PyTorch with transfer learning (ResNet18).
"""
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from PIL import Image
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "data" / "ml_dataset"
MODEL_DIR = ROOT / "models"

class OSRSDataset(Dataset):
    """Dataset for OSRS images organized in folders"""

    def __init__(self, root_dir, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []
        self.classes = []
        self.class_to_idx = {}

        # Walk through folder structure
        for category_dir in sorted(self.root_dir.rglob("*")):
            if not category_dir.is_dir():
                continue

            images = list(category_dir.glob("*.png")) + list(category_dir.glob("*.jpg"))
            if not images:
                continue

            # Use relative path as class name (e.g., "trees/oak")
            class_name = str(category_dir.relative_to(self.root_dir)).replace("\\", "/")

            if class_name not in self.class_to_idx:
                self.class_to_idx[class_name] = len(self.classes)
                self.classes.append(class_name)

            idx = self.class_to_idx[class_name]
            for img_path in images:
                self.samples.append((str(img_path), idx))

        print(f"Found {len(self.samples)} images in {len(self.classes)} classes")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        try:
            image = Image.open(img_path).convert('RGB')
        except:
            # Return blank image on error
            image = Image.new('RGB', (64, 64), (0, 0, 0))

        if self.transform:
            image = self.transform(image)

        return image, label

def create_model(num_classes, pretrained=True):
    """Create a ResNet18 model for classification"""
    model = models.resnet18(weights='IMAGENET1K_V1' if pretrained else None)

    # Replace final layer for our number of classes
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, num_classes)

    return model

def train_model(model, train_loader, num_epochs=10, device='cpu'):
    """Train the model"""
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        acc = 100. * correct / total
        avg_loss = running_loss / len(train_loader)
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {avg_loss:.4f} - Acc: {acc:.2f}%")

    return model

def save_model(model, classes, save_path):
    """Save model and class mapping"""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    torch.save({
        'model_state_dict': model.state_dict(),
        'classes': classes,
        'num_classes': len(classes)
    }, save_path)

    # Also save class mapping as JSON
    mapping_path = save_path.with_suffix('.json')
    with open(mapping_path, 'w') as f:
        json.dump({'classes': classes}, f, indent=2)

    print(f"Model saved to {save_path}")

def main():
    print("=" * 50)
    print("OSRS Image Classifier Training")
    print("=" * 50)

    # Check for GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")

    # Data transforms
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                           std=[0.229, 0.224, 0.225])
    ])

    # Load dataset
    print(f"\nLoading dataset from {DATASET_DIR}")
    dataset = OSRSDataset(DATASET_DIR, transform=transform)

    if len(dataset) == 0:
        print("ERROR: No images found in dataset!")
        print("Run download_wiki_images.py first to populate the dataset.")
        return

    print(f"\nClasses found:")
    for i, cls in enumerate(dataset.classes):
        count = sum(1 for s in dataset.samples if s[1] == i)
        print(f"  {i}: {cls} ({count} images)")

    # Create data loader
    train_loader = DataLoader(dataset, batch_size=16, shuffle=True, num_workers=0)

    # Create model
    print(f"\nCreating model with {len(dataset.classes)} classes...")
    model = create_model(len(dataset.classes), pretrained=True)

    # Train
    print("\nTraining...")
    model = train_model(model, train_loader, num_epochs=10, device=device)

    # Save model
    save_path = MODEL_DIR / "osrs_classifier.pth"
    save_model(model, dataset.classes, save_path)

    print("\nTraining complete!")

if __name__ == "__main__":
    main()
