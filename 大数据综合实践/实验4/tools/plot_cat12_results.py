#!/usr/bin/env python
"""Plot Cat12 training curves and evaluation charts from saved CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-csv", required=True, help="Path to metrics.csv")
    parser.add_argument(
        "--confusion-csv",
        default="",
        help="Optional confusion matrix csv from eval mode.",
    )
    parser.add_argument(
        "--class-metrics-csv",
        default="",
        help="Optional per-class metrics csv from eval mode.",
    )
    parser.add_argument("--out-dir", default="", help="Output directory for figures.")
    parser.add_argument("--title", default="Cat12", help="Figure title prefix.")
    return parser.parse_args()


def ensure_out_dir(path: str | Path, metrics_csv: Path) -> Path:
    out_dir = Path(path) if path else metrics_csv.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def plot_training_curves(df: pd.DataFrame, out_path: Path, title: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)

    axes[0].plot(df["epoch"], df["train_loss"], marker="o", label="train")
    axes[0].plot(df["epoch"], df["val_loss"], marker="o", label="val")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].plot(df["epoch"], df["train_top1"], marker="o", label="train top1")
    axes[1].plot(df["epoch"], df["val_top1"], marker="o", label="val top1")
    axes[1].plot(df["epoch"], df["train_top3"], marker="o", label="train top3")
    axes[1].plot(df["epoch"], df["val_top3"], marker="o", label="val top3")
    axes[1].set_title("Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].set_ylim(0.0, 1.05)
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()

    axes[2].plot(df["epoch"], df["lr"], marker="o", color="#7b3294")
    axes[2].set_title("Learning Rate")
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("LR")
    axes[2].grid(True, alpha=0.25)

    fig.suptitle(title, fontsize=14)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_confusion_matrix(confusion_csv: Path, out_path: Path, title: str) -> None:
    df = pd.read_csv(confusion_csv)
    labels = [str(v) for v in df.iloc[:, 0].tolist()]
    matrix = df.iloc[:, 1:].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(8.8, 7.4), constrained_layout=True)
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_title(title)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    threshold = matrix.max() * 0.5 if matrix.size else 0.0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = int(matrix[i, j])
            ax.text(
                j,
                i,
                value,
                ha="center",
                va="center",
                color="white" if matrix[i, j] > threshold else "black",
                fontsize=8,
            )

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_class_metrics(class_metrics_csv: Path, out_path: Path, title: str) -> None:
    df = pd.read_csv(class_metrics_csv)
    x = np.arange(len(df))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 4.8), constrained_layout=True)
    ax.bar(x - width, df["precision"], width, label="Precision")
    ax.bar(x, df["recall"], width, label="Recall")
    ax.bar(x + width, df["f1"], width, label="F1")
    ax.set_title(title)
    ax.set_xlabel("Class")
    ax.set_ylabel("Score")
    ax.set_ylim(0.0, 1.05)
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in df["class_id"].tolist()])
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()

    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    metrics_csv = Path(args.metrics_csv)
    if not metrics_csv.is_file():
        raise FileNotFoundError(metrics_csv)

    out_dir = ensure_out_dir(args.out_dir, metrics_csv)
    df = pd.read_csv(metrics_csv).sort_values("epoch")
    plot_training_curves(df, out_dir / "training_curves.png", f"{args.title} Training Curves")
    print(f"Wrote {out_dir / 'training_curves.png'}")

    if args.confusion_csv:
        confusion_csv = Path(args.confusion_csv)
        if not confusion_csv.is_file():
            raise FileNotFoundError(confusion_csv)
        plot_confusion_matrix(
            confusion_csv, out_dir / "confusion_matrix.png", f"{args.title} Confusion Matrix"
        )
        print(f"Wrote {out_dir / 'confusion_matrix.png'}")

    if args.class_metrics_csv:
        class_metrics_csv = Path(args.class_metrics_csv)
        if not class_metrics_csv.is_file():
            raise FileNotFoundError(class_metrics_csv)
        plot_class_metrics(
            class_metrics_csv, out_dir / "class_metrics.png", f"{args.title} Class Metrics"
        )
        print(f"Wrote {out_dir / 'class_metrics.png'}")


if __name__ == "__main__":
    main()
