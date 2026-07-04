#!/usr/bin/env python
"""Fine-tune high-accuracy PaddleClas models for the 12-class cat dataset."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

import numpy as np
from PIL import Image

import paddle
import paddle.nn.functional as F
from paddle.io import DataLoader, Dataset
from paddle.vision import transforms as T

from paddleclas.ppcls.arch.backbone.model_zoo.cswin_transformer import (
    CSWinTransformer_large_384,
)
from paddleclas.ppcls.arch.backbone.legendary_models.swin_transformer import (
    SwinTransformer_large_patch4_window12_384,
)
from paddleclas.ppcls.utils.save_load import load_dygraph_pretrain


MODEL_SPECS = {
    "cswin_large_384": {
        "builder": CSWinTransformer_large_384,
        "title": "CSWinTransformer_large_384",
        "slug": "cswin_large_384",
        "pretrained_url": (
            "https://paddle-imagenet-models-name.bj.bcebos.com/dygraph/"
            "CSWinTransformer_large_384_pretrained.pdparams"
        ),
    },
    "swin_large_384_22kto1k": {
        "builder": SwinTransformer_large_patch4_window12_384,
        "title": "SwinTransformer_large_patch4_window12_384_22kto1k",
        "slug": "swin_large_384_22kto1k",
        "pretrained_url": "auto",
    },
}


class Cat12Dataset(Dataset):
    def __init__(self, root: str | Path, list_path: str | Path, transform=None):
        self.root = Path(root)
        self.list_path = Path(list_path)
        self.transform = transform
        self.samples: list[tuple[Path, int]] = []

        for line_no, raw_line in enumerate(
            self.list_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            parts = raw_line.strip().split()
            if len(parts) != 2:
                raise ValueError(f"Bad line {line_no} in {self.list_path}: {raw_line}")
            rel_path, label = parts
            image_path = self.root / rel_path
            if not image_path.is_file():
                raise FileNotFoundError(f"Missing image: {image_path}")
            self.samples.append((image_path, int(label)))

        if not self.samples:
            raise ValueError(f"No samples found in {self.list_path}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        image_path, label = self.samples[index]
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            if self.transform is not None:
                image = self.transform(image)
        return image, np.int64(label)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--train-list", default="paddleclas_data/train_list.txt")
    parser.add_argument("--val-list", default="paddleclas_data/val_list.txt")
    parser.add_argument("--model", default="cswin_large_384", choices=sorted(MODEL_SPECS))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--class-num", type=int, default=12)
    parser.add_argument("--image-size", type=int, default=384)
    parser.add_argument("--epochs", type=int, default=36)
    parser.add_argument("--freeze-epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--accum-steps", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--head-lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--device", default="gpu", choices=["gpu", "cpu"])
    parser.add_argument("--amp", action="store_true", default=True)
    parser.add_argument("--no-amp", action="store_false", dest="amp")
    parser.add_argument(
        "--pretrained",
        default="auto",
        help="auto, none, URL, or path prefix/path to .pdparams.",
    )
    parser.add_argument(
        "--resume",
        default="",
        help=(
            "Resume from checkpoint prefix or .pdparams path, for example "
            "output/cat12_cswin_large_384/last or "
            "output/cat12_cswin_large_384/last.pdparams."
        ),
    )
    parser.add_argument("--save-every", type=int, default=0)
    parser.add_argument(
        "--metrics-csv",
        default="",
        help="Epoch metrics csv path. Defaults to <output-dir>/metrics.csv.",
    )
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    paddle.seed(seed)


def build_transforms(image_size: int):
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    train_transform = T.Compose(
        [
            T.RandomResizedCrop(
                image_size,
                scale=(0.75, 1.0),
                ratio=(0.75, 1.3333333333333333),
            ),
            T.RandomHorizontalFlip(prob=0.5),
            T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ]
    )
    val_transform = T.Compose(
        [
            T.Resize(round(image_size / 0.875)),
            T.CenterCrop(image_size),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ]
    )
    return train_transform, val_transform


def build_model(model_name: str, class_num: int, pretrained: str):
    spec = MODEL_SPECS[model_name]
    builder = spec["builder"]

    if pretrained == "auto" and spec["pretrained_url"] == "auto":
        print(f"Loading PaddleClas pretrained weights: {spec['title']}")
        if model_name.startswith("swin_"):
            model = builder(pretrained=True, class_num=1000)
        else:
            model = builder(pretrained=True, class_num=1000)
    else:
        if model_name.startswith("swin_"):
            model = builder(pretrained=False, class_num=1000)
        else:
            model = builder(pretrained=False, class_num=1000)

        if pretrained.lower() not in {"none", "false", "0"}:
            pretrain_path = spec["pretrained_url"] if pretrained == "auto" else pretrained
            print(f"Loading pretrained weights: {pretrain_path}")
            load_dygraph_pretrain(model, pretrain_path)

    in_features = int(model.head.weight.shape[0])
    model.head = paddle.nn.Linear(in_features, class_num)
    return model


def set_backbone_trainable(model: paddle.nn.Layer, trainable: bool) -> None:
    for name, param in model.named_parameters():
        if not name.startswith("head."):
            param.stop_gradient = not trainable


def make_optimizer(model: paddle.nn.Layer, lr: float, weight_decay: float, steps: int):
    steps = max(1, steps)
    scheduler = paddle.optimizer.lr.CosineAnnealingDecay(learning_rate=lr, T_max=steps)
    optimizer = paddle.optimizer.AdamW(
        learning_rate=scheduler,
        beta1=0.9,
        beta2=0.999,
        epsilon=1e-8,
        parameters=[p for p in model.parameters() if not p.stop_gradient],
        weight_decay=weight_decay,
    )
    return optimizer, scheduler


def smooth_cross_entropy(logits, labels, class_num: int, epsilon: float):
    if epsilon <= 0:
        return F.cross_entropy(logits, labels)
    labels = labels.astype("int64")
    one_hot = F.one_hot(labels, num_classes=class_num).astype("float32")
    soft_labels = one_hot * (1.0 - epsilon) + epsilon / class_num
    log_probs = F.log_softmax(logits, axis=1)
    return -(soft_labels * log_probs).sum(axis=1).mean()


def topk_counts(logits, labels, ks=(1, 3)):
    max_k = min(max(ks), logits.shape[1])
    _, pred = paddle.topk(logits, k=max_k, axis=1)
    labels = labels.reshape([-1, 1])
    counts = {}
    for k in ks:
        k = min(k, logits.shape[1])
        correct = (pred[:, :k] == labels).astype("int64").sum(axis=1)
        counts[k] = int((correct > 0).astype("int64").sum().numpy())
    return counts


@paddle.no_grad()
def evaluate(model, loader, class_num: int, label_smoothing: float, max_batches: int = 0):
    model.eval()
    loss_sum = 0.0
    total = 0
    correct1 = 0
    correct3 = 0

    for batch_idx, (images, labels) in enumerate(loader, start=1):
        logits = model(images)
        loss = smooth_cross_entropy(logits, labels, class_num, label_smoothing)
        batch_size = labels.shape[0]
        counts = topk_counts(logits, labels, ks=(1, 3))
        loss_sum += float(loss.numpy()) * batch_size
        total += batch_size
        correct1 += counts[1]
        correct3 += counts[3]
        if max_batches and batch_idx >= max_batches:
            break

    return {
        "loss": loss_sum / max(1, total),
        "top1": correct1 / max(1, total),
        "top3": correct3 / max(1, total),
    }


def save_checkpoint(path: Path, model, optimizer, epoch: int, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    paddle.save(model.state_dict(), str(path.with_suffix(".pdparams")))
    paddle.save(optimizer.state_dict(), str(path.with_suffix(".pdopt")))
    path.with_suffix(".json").write_text(
        json.dumps({"epoch": epoch, "metrics": metrics}, indent=2),
        encoding="utf-8",
    )


def train_one_epoch(
    model,
    loader,
    optimizer,
    scheduler,
    scaler,
    args,
    epoch: int,
    use_amp: bool,
):
    model.train()
    tic = time.time()
    loss_meter = 0.0
    total = 0
    correct1 = 0
    correct3 = 0
    last_lr = optimizer.get_lr()
    optimizer.clear_grad()

    for step, (images, labels) in enumerate(loader, start=1):
        with paddle.amp.auto_cast(enable=use_amp, level="O1"):
            logits = model(images)
            loss = smooth_cross_entropy(
                logits, labels, args.class_num, args.label_smoothing
            )
            loss_for_backward = loss / args.accum_steps

        if use_amp:
            scaled = scaler.scale(loss_for_backward)
            scaled.backward()
        else:
            loss_for_backward.backward()

        should_update = step % args.accum_steps == 0 or step == len(loader)
        if should_update:
            if use_amp:
                scaler.minimize(optimizer, scaled)
            else:
                optimizer.step()
            optimizer.clear_grad()
            scheduler.step()
            last_lr = optimizer.get_lr()

        batch_size = labels.shape[0]
        counts = topk_counts(logits, labels, ks=(1, 3))
        loss_meter += float(loss.numpy()) * batch_size
        total += batch_size
        correct1 += counts[1]
        correct3 += counts[3]

        if step == 1 or step % 20 == 0 or step == len(loader):
            print(
                f"epoch {epoch:03d} step {step:04d}/{len(loader)} "
                f"loss {loss_meter / total:.4f} "
                f"top1 {correct1 / total:.4f} top3 {correct3 / total:.4f} "
                f"lr {last_lr:.2e}"
            )

        if args.smoke_test and step >= 2:
            break

    return {
        "loss": loss_meter / max(1, total),
        "top1": correct1 / max(1, total),
        "top3": correct3 / max(1, total),
        "seconds": time.time() - tic,
        "lr": last_lr,
    }


def append_metrics_row(path: Path, row: dict, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    need_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if need_header:
            writer.writeheader()
        writer.writerow(row)


def resolve_checkpoint_paths(resume: str) -> tuple[Path, Path, Path]:
    path = Path(resume)
    prefix = path.with_suffix("") if path.suffix == ".pdparams" else path
    return (
        prefix.with_suffix(".pdparams"),
        prefix.with_suffix(".pdopt"),
        prefix.with_suffix(".json"),
    )


def read_checkpoint_epoch(path: Path) -> int:
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("epoch", 0))


def read_best_state(output_dir: Path) -> tuple[int, float]:
    path = output_dir / "best.json"
    if not path.is_file():
        return 0, -1.0
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("epoch", 0)), float(data["metrics"]["val"]["top1"])


def trim_metrics_csv(path: Path, start_epoch: int) -> None:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return
        rows = [row for row in reader if int(row.get("epoch", 0)) < start_epoch]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def phase_for_epoch(epoch: int, freeze_epochs: int) -> str:
    if freeze_epochs > 0 and epoch <= freeze_epochs:
        return "head"
    return "full"


def advance_scheduler(scheduler, steps: int) -> None:
    for _ in range(max(0, steps)):
        scheduler.step()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    if args.device == "gpu" and not paddle.device.is_compiled_with_cuda():
        raise RuntimeError("Paddle was not compiled with CUDA. Use --device cpu.")
    paddle.set_device(args.device)

    output_dir = Path(args.output_dir or f"output/cat12_{MODEL_SPECS[args.model]['slug']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_csv = Path(args.metrics_csv) if args.metrics_csv else output_dir / "metrics.csv"
    if not args.resume and metrics_csv.exists():
        metrics_csv.unlink()

    train_transform, val_transform = build_transforms(args.image_size)
    train_set = Cat12Dataset(args.root, args.train_list, train_transform)
    val_set = Cat12Dataset(args.root, args.val_list, val_transform)

    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=max(1, args.batch_size),
        shuffle=False,
        num_workers=args.num_workers,
        drop_last=False,
    )

    updates_per_epoch = math.ceil(len(train_loader) / max(1, args.accum_steps))
    print(f"Model: {MODEL_SPECS[args.model]['title']}")
    model = build_model(args.model, args.class_num, args.pretrained)
    resume_epoch = 0
    resume_opt_path: Path | None = None
    if args.resume:
        resume_params_path, resume_opt_path, resume_json_path = resolve_checkpoint_paths(
            args.resume
        )
        if not resume_params_path.is_file():
            raise FileNotFoundError(f"Missing resume weights: {resume_params_path}")
        print(f"Resuming weights from: {resume_params_path}")
        model.set_state_dict(paddle.load(str(resume_params_path)))
        resume_epoch = read_checkpoint_epoch(resume_json_path)
        if resume_epoch:
            print(f"Resume checkpoint epoch: {resume_epoch}")
        else:
            print("Resume checkpoint epoch is unknown; training will start at epoch 1.")

    use_amp = bool(args.amp and args.device == "gpu")
    scaler = paddle.amp.GradScaler(enable=use_amp, init_loss_scaling=128.0)
    best_epoch, best_top1 = read_best_state(output_dir)
    metrics_fieldnames = [
        "epoch",
        "model_name",
        "phase",
        "train_loss",
        "train_top1",
        "train_top3",
        "val_loss",
        "val_top1",
        "val_top3",
        "lr",
        "seconds",
        "best_flag",
        "best_epoch",
        "best_top1",
    ]

    args.freeze_epochs = min(args.freeze_epochs, args.epochs)
    start_epoch = resume_epoch + 1 if resume_epoch else 1
    if start_epoch > args.epochs:
        print(
            f"Checkpoint is already at epoch {resume_epoch}; "
            f"--epochs is {args.epochs}, so there is nothing to train."
        )
        return
    if args.resume:
        trim_metrics_csv(metrics_csv, start_epoch)

    def configure_optimizer(epoch: int):
        phase_name = phase_for_epoch(epoch, args.freeze_epochs)
        if phase_name == "head":
            print(
                f"Phase 1: train classifier head through epoch {args.freeze_epochs} "
                f"(starting at epoch {epoch})"
            )
            set_backbone_trainable(model, trainable=False)
            optimizer_, scheduler_ = make_optimizer(
                model,
                lr=args.head_lr,
                weight_decay=args.weight_decay,
                steps=args.freeze_epochs * updates_per_epoch,
            )
            completed_epochs = epoch - 1
        else:
            if args.freeze_epochs > 0:
                print(
                    f"Phase 2: fine-tune full {MODEL_SPECS[args.model]['title']} "
                    f"through epoch {args.epochs} (starting at epoch {epoch})"
                )
            else:
                print("Phase 1 skipped")
            set_backbone_trainable(model, trainable=True)
            phase_epochs = max(1, args.epochs - args.freeze_epochs)
            optimizer_, scheduler_ = make_optimizer(
                model,
                lr=args.lr,
                weight_decay=args.weight_decay,
                steps=phase_epochs * updates_per_epoch,
            )
            completed_epochs = max(0, epoch - args.freeze_epochs - 1)
        advance_scheduler(scheduler_, completed_epochs * updates_per_epoch)
        return phase_name, optimizer_, scheduler_

    phase, optimizer, scheduler = configure_optimizer(start_epoch)
    if args.resume and resume_opt_path and resume_opt_path.is_file():
        resume_phase = phase_for_epoch(resume_epoch, args.freeze_epochs)
        if resume_phase == phase:
            print(f"Resuming optimizer state from: {resume_opt_path}")
            optimizer.set_state_dict(paddle.load(str(resume_opt_path)))
        else:
            print(
                "Checkpoint crosses into a new training phase; "
                "starting a fresh optimizer for the current phase."
            )

    for epoch in range(start_epoch, args.epochs + 1):
        epoch_phase = phase_for_epoch(epoch, args.freeze_epochs)
        if epoch_phase != phase:
            phase, optimizer, scheduler = configure_optimizer(epoch)

        train_metrics = train_one_epoch(
            model, train_loader, optimizer, scheduler, scaler, args, epoch, use_amp
        )
        val_metrics = evaluate(
            model,
            val_loader,
            args.class_num,
            0.0,
            max_batches=2 if args.smoke_test else 0,
        )
        metrics = {"train": train_metrics, "val": val_metrics}
        is_best = val_metrics["top1"] > best_top1
        if is_best:
            best_top1 = val_metrics["top1"]
            best_epoch = epoch
        print(
            f"epoch {epoch:03d} done "
            f"train_top1 {train_metrics['top1']:.4f} "
            f"val_top1 {val_metrics['top1']:.4f} "
            f"val_top3 {val_metrics['top3']:.4f}"
        )

        save_checkpoint(output_dir / "last", model, optimizer, epoch, metrics)
        if is_best:
            save_checkpoint(output_dir / "best", model, optimizer, epoch, metrics)
            print(f"saved new best: top1={best_top1:.4f}")
        if args.save_every and epoch % args.save_every == 0:
            save_checkpoint(output_dir / f"epoch_{epoch:03d}", model, optimizer, epoch, metrics)

        append_metrics_row(
            metrics_csv,
            {
                "epoch": epoch,
                "model_name": args.model,
                "phase": phase,
                "train_loss": train_metrics["loss"],
                "train_top1": train_metrics["top1"],
                "train_top3": train_metrics["top3"],
                "val_loss": val_metrics["loss"],
                "val_top1": val_metrics["top1"],
                "val_top3": val_metrics["top3"],
                "lr": train_metrics["lr"],
                "seconds": train_metrics["seconds"],
                "best_flag": int(is_best),
                "best_epoch": best_epoch,
                "best_top1": best_top1,
            },
            metrics_fieldnames,
        )

        if args.smoke_test:
            print("Smoke test finished after one epoch.")
            break

    print(f"Epoch metrics written to: {metrics_csv}")


if __name__ == "__main__":
    main()
