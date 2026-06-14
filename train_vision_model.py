"""Train and evaluate the 36-class VisualAgro produce classifier using MobileNetV3."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

from phase4.produce_classifier import ProduceClassifier


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_SIZE = 160
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]


class DirectoryImageDataset(Dataset):
    def __init__(self, root: Path, class_names: list[str], transform: T.Compose | None = None):
        self.root = root
        self.class_names = class_names
        self.transform = transform
        self.samples: list[tuple[Path, int]] = []
        for class_index, class_name in enumerate(class_names):
            class_dir = root / class_name
            for path in sorted(class_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.samples.append((path, class_index))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        with Image.open(path) as source:
            image = source.convert("RGB")
            if self.transform:
                tensor = self.transform(image)
            else:
                image = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
                array = np.asarray(image, dtype=np.float32) / 255.0
                tensor = torch.from_numpy(array).permute(2, 0, 1)
                tensor = (tensor - 0.5) / 0.5
        return tensor, label


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    loss_sum = 0.0
    correct = 0
    count = 0

    for inputs, labels in loader:
        inputs = inputs.to(device)
        labels = labels.to(device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(inputs)
            loss = criterion(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
        batch_size = labels.size(0)
        loss_sum += loss.item() * batch_size
        correct += (logits.argmax(dim=1) == labels).sum().item()
        count += batch_size

    return loss_sum / max(count, 1), correct / max(count, 1)


def save_plot(history: dict[str, list[float]], output_path: Path) -> None:
    epochs = range(1, len(history["train_loss"]) + 1)
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(epochs, history["train_accuracy"], label="train")
    axes[0].plot(epochs, history["validation_accuracy"], label="validation")
    axes[0].set(title="Accuracy", xlabel="Epoch", ylabel="Accuracy")
    axes[0].legend()
    axes[1].plot(epochs, history["train_loss"], label="train")
    axes[1].plot(epochs, history["validation_loss"], label="validation")
    axes[1].set(title="Loss", xlabel="Epoch", ylabel="Loss")
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[2] / "archive (1)")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "ai_artifacts")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))

    class_names = sorted(path.name for path in (args.data / "train").iterdir() if path.is_dir())
    if not class_names:
        raise RuntimeError(f"No class folders found under {args.data / 'train'}")
    for split in ("validation", "test"):
        split_classes = sorted(path.name for path in (args.data / split).iterdir() if path.is_dir())
        if split_classes != class_names:
            raise RuntimeError(f"Class folders in {split} do not match train")

    # Define robust transforms
    train_transform = T.Compose([
        T.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
        T.RandomHorizontalFlip(),
        T.RandomRotation(15),
        T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        T.ToTensor(),
        T.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    eval_transform = T.Compose([
        T.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        T.CenterCrop(IMAGE_SIZE),
        T.ToTensor(),
        T.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    datasets = {
        "train": DirectoryImageDataset(args.data / "train", class_names, transform=train_transform),
        "validation": DirectoryImageDataset(args.data / "validation", class_names, transform=eval_transform),
        "test": DirectoryImageDataset(args.data / "test", class_names, transform=eval_transform),
    }
    loaders = {
        name: DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=name == "train",
            num_workers=args.workers,
            pin_memory=False,
            persistent_workers=args.workers > 0,
        )
        for name, dataset in datasets.items()
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ProduceClassifier(len(class_names), pretrained=True).to(device)

    # Freeze earlier layers in feature extractor, fine-tune the classifier head and last feature blocks
    for param in model.model.features.parameters():
        param.requires_grad = False
    # Unfreeze last block of the feature extractor (features[-1] and features[-2])
    for param in model.model.features[-2:].parameters():
        param.requires_grad = True

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    # Filter optimizer to only update trainable parameters
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=args.learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", patience=2, factor=0.5)
    
    history: dict[str, list[float]] = {
        "train_loss": [],
        "train_accuracy": [],
        "validation_loss": [],
        "validation_accuracy": [],
    }
    best_state = None
    best_accuracy = -1.0
    started = time.time()
    patience = 3
    epochs_no_improve = 0

    print(f"device={device} classes={len(class_names)} samples={ {key: len(value) for key, value in datasets.items()} }")
    for epoch in range(1, args.epochs + 1):
        train_loss, train_accuracy = run_epoch(model, loaders["train"], criterion, device, optimizer)
        validation_loss, validation_accuracy = run_epoch(model, loaders["validation"], criterion, device)
        scheduler.step(validation_accuracy)
        history["train_loss"].append(train_loss)
        history["train_accuracy"].append(train_accuracy)
        history["validation_loss"].append(validation_loss)
        history["validation_accuracy"].append(validation_accuracy)
        
        print(
            f"epoch={epoch}/{args.epochs} train_loss={train_loss:.4f} train_acc={train_accuracy:.4f} "
            f"val_loss={validation_loss:.4f} val_acc={validation_accuracy:.4f}"
        )

        if validation_accuracy > best_accuracy:
            best_accuracy = validation_accuracy
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"Early stopping triggered at epoch {epoch} (no val_acc improvement for {patience} epochs).")
                break

    if best_state is None:
        raise RuntimeError("Training did not produce a model")
    
    model.load_state_dict(best_state)
    test_loss, test_accuracy = run_epoch(model, loaders["test"], criterion, device)

    # Compute per-class evaluation metrics
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for inputs, labels in loaders["test"]:
            inputs = inputs.to(device)
            logits = model(inputs)
            preds = logits.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    print("\n" + "="*70)
    print(" PER-CLASS EVALUATION METRICS (TEST SET) ".center(70, "="))
    print(f"{'Class Name':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 70)

    per_class_metrics = {}
    for class_index, class_name in enumerate(class_names):
        true_positives = np.sum((all_labels == class_index) & (all_preds == class_index))
        false_positives = np.sum((all_labels != class_index) & (all_preds == class_index))
        false_negatives = np.sum((all_labels == class_index) & (all_preds != class_index))
        support = np.sum(all_labels == class_index)

        precision = float(true_positives / (true_positives + false_positives)) if (true_positives + false_positives) > 0 else 0.0
        recall = float(true_positives / (true_positives + false_negatives)) if (true_positives + false_negatives) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class_metrics[class_name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": int(support),
        }
        print(f"{class_name:<22} | {precision:.4f}     | {recall:.4f}     | {f1:.4f}     | {support:<8}")
    print("=" * 70 + "\n")

    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output / "produce_classifier.pt"
    history_path = args.output / "produce_classifier_history.json"
    plot_path = args.output / "produce_classifier_metrics.png"
    
    checkpoint = {
        "state_dict": best_state,
        "class_names": class_names,
        "image_size": IMAGE_SIZE,
        "normalization": {"mean": NORM_MEAN, "std": NORM_STD},
        "validation_accuracy": best_accuracy,
        "test_accuracy": test_accuracy,
    }
    torch.save(checkpoint, checkpoint_path)
    
    metrics = {
        **history,
        "class_names": class_names,
        "image_size": IMAGE_SIZE,
        "normalization": {"mean": NORM_MEAN, "std": NORM_STD},
        "best_validation_accuracy": best_accuracy,
        "test_loss": test_loss,
        "test_accuracy": test_accuracy,
        "elapsed_seconds": round(time.time() - started, 2),
        "dataset_counts": {key: len(value) for key, value in datasets.items()},
        "per_class_metrics": per_class_metrics,
    }
    history_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    save_plot(history, plot_path)
    print(f"test_loss={test_loss:.4f} test_acc={test_accuracy:.4f}")
    print(f"saved={checkpoint_path}")


if __name__ == "__main__":
    main()
