#!/usr/bin/env python
"""Predict test images with single-model or ensemble TTA logits averaging."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

import paddle
from paddle.io import DataLoader, Dataset
from paddle.vision import transforms as T

from paddleclas.ppcls.arch.backbone.model_zoo.cswin_transformer import (
    CSWinTransformer_large_384,
)
from paddleclas.ppcls.arch.backbone.legendary_models.swin_transformer import (
    SwinTransformer_large_patch4_window12_384,
)


MODEL_BUILDERS = {
    "cswin_large_384": lambda class_num: CSWinTransformer_large_384(
        pretrained=False, class_num=class_num
    ),
    "swin_large_384_22kto1k": lambda class_num: SwinTransformer_large_patch4_window12_384(
        pretrained=False, class_num=class_num
    ),
}


class HorizontalFlip:
    def __call__(self, image):
        return ImageOps.mirror(image)


def load_samples(
    root: str | Path, list_path: str | Path, with_labels: bool
) -> list[tuple[str, Path, int | None]]:
    root_path = Path(root)
    samples: list[tuple[str, Path, int | None]] = []
    for line_no, raw_line in enumerate(
        Path(list_path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        parts = raw_line.strip().split()
        if with_labels and len(parts) != 2:
            raise ValueError(f"Bad labeled line {line_no} in {list_path}: {raw_line}")
        if not with_labels and len(parts) != 1:
            raise ValueError(f"Bad image line {line_no} in {list_path}: {raw_line}")
        rel_path = parts[0].replace("\\", "/")
        label = int(parts[1]) if with_labels else None
        image_path = root_path / rel_path
        if not image_path.is_file():
            raise FileNotFoundError(f"Missing image: {image_path}")
        samples.append((rel_path, image_path, label))
    if not samples:
        raise ValueError(f"No images found in {list_path}")
    return samples


class ImageListDataset(Dataset):
    def __init__(
        self,
        samples: list[tuple[str, Path, int | None]],
        transform=None,
        with_labels: bool = False,
    ):
        self.samples = samples
        self.transform = transform
        self.with_labels = with_labels

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        rel_path, image_path, label = self.samples[index]
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            if self.transform is not None:
                image = self.transform(image)
        if self.with_labels:
            return image, np.int64(index), rel_path, np.int64(label)
        return image, np.int64(index), rel_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--test-list", default="paddleclas_data/test_images.txt")
    parser.add_argument(
        "--weights",
        action="append",
        default=[],
        help=(
            "Model weight in model=path format. Repeat for ensemble. "
            "Supported models: cswin_large_384, swin_large_384_22kto1k. "
            "A bare path is treated as cswin_large_384."
        ),
    )
    parser.add_argument("--output", default="result.csv")
    parser.add_argument(
        "--eval-list",
        default="",
        help="Optional labeled list file for validation evaluation.",
    )
    parser.add_argument(
        "--predictions-output",
        default="",
        help="Predictions csv for eval mode. Defaults to val_predictions.csv.",
    )
    parser.add_argument(
        "--metrics-output",
        default="",
        help="Summary json for eval mode. Defaults to val_metrics.json.",
    )
    parser.add_argument(
        "--confusion-output",
        default="",
        help="Confusion matrix csv for eval mode. Defaults to confusion_matrix.csv.",
    )
    parser.add_argument(
        "--class-metrics-output",
        default="",
        help="Per-class metrics csv for eval mode. Defaults to class_metrics.csv.",
    )
    parser.add_argument("--class-num", type=int, default=12)
    parser.add_argument("--image-size", type=int, default=384)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", default="gpu", choices=["gpu", "cpu"])
    parser.add_argument(
        "--tta",
        default="flip",
        choices=["none", "flip", "multiscale"],
        help="none: center crop only; flip: center + hflip; multiscale: 3 scales x 2 flips.",
    )
    parser.add_argument("--amp", action="store_true", default=True)
    parser.add_argument("--no-amp", action="store_false", dest="amp")
    return parser.parse_args()


def build_transform(image_size: int, resize_short: int, flip: bool):
    ops = [
        T.Resize(resize_short),
        T.CenterCrop(image_size),
    ]
    if flip:
        ops.append(HorizontalFlip())
    ops.extend(
        [
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return T.Compose(ops)


def build_tta_transforms(image_size: int, tta: str):
    base_short = round(image_size / 0.875)
    if tta == "none":
        settings = [(base_short, False)]
    elif tta == "flip":
        settings = [(base_short, False), (base_short, True)]
    else:
        settings = [
            (base_short, False),
            (base_short, True),
            (480, False),
            (480, True),
            (512, False),
            (512, True),
        ]
    return [
        (f"resize{resize_short}_{'flip' if flip else 'plain'}", build_transform(image_size, resize_short, flip))
        for resize_short, flip in settings
    ]


def softmax_np(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def parse_weight_specs(raw_weights: list[str]) -> list[tuple[str, Path]]:
    if not raw_weights:
        raw_weights = ["cswin_large_384=output/cat12_cswin_large_384/best.pdparams"]

    specs: list[tuple[str, Path]] = []
    for raw in raw_weights:
        if "=" in raw:
            model_name, path = raw.split("=", 1)
        else:
            model_name, path = "cswin_large_384", raw
        model_name = model_name.strip()
        if model_name not in MODEL_BUILDERS:
            raise ValueError(
                f"Unsupported model {model_name!r}. Choose from {sorted(MODEL_BUILDERS)}"
            )
        weight_path = Path(path.strip())
        if not weight_path.is_file():
            raise FileNotFoundError(f"Missing weights: {weight_path}")
        specs.append((model_name, weight_path))
    return specs


def checkpoint_class_num(state_dict, fallback: int) -> int:
    head_weight = state_dict.get("head.weight")
    if head_weight is None:
        return fallback
    if len(head_weight.shape) != 2:
        return fallback
    return int(head_weight.shape[1])


def build_model(model_name: str, class_num: int, weight_path: Path):
    state_dict = paddle.load(str(weight_path))
    ckpt_class_num = checkpoint_class_num(state_dict, class_num)
    if ckpt_class_num != class_num:
        print(
            f"  checkpoint head has {ckpt_class_num} classes; "
            f"using first {class_num} logits for ensemble"
        )
    model = MODEL_BUILDERS[model_name](ckpt_class_num)
    model.set_state_dict(state_dict)
    model.eval()
    return model


def model_tag(weight_specs: list[tuple[str, Path]]) -> str:
    names = [name for name, _ in weight_specs]
    if len(names) == 1:
        return names[0]
    return "ensemble:" + "+".join(names)


def collect_samples(
    args, list_path: str | Path, with_labels: bool
) -> list[tuple[str, Path, int | None]]:
    return load_samples(args.root, list_path, with_labels=with_labels)


@paddle.no_grad()
def aggregate_logits(model, samples, args, transforms, with_labels: bool):
    logits_sum = np.zeros((len(samples), args.class_num), dtype="float64")
    labels = np.full(len(samples), -1, dtype=np.int64) if with_labels else None
    warned = False
    for view_name, transform in transforms:
        dataset = ImageListDataset(samples, transform=transform, with_labels=with_labels)
        loader = DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            drop_last=False,
        )
        print(f"  TTA view: {view_name}")
        for batch in loader:
            if with_labels:
                images, indices, _, batch_labels = batch
                labels[indices.numpy()] = batch_labels.numpy()
            else:
                images, indices, _ = batch
            with paddle.amp.auto_cast(
                enable=bool(args.amp and args.device == "gpu"), level="O1"
            ):
                logits = model(images)
            if logits.shape[1] != args.class_num:
                if logits.shape[1] < args.class_num:
                    raise ValueError(
                        f"Model returned {logits.shape[1]} logits, "
                        f"but class_num is {args.class_num}."
                    )
                if not warned:
                    print(
                        f"  slicing logits from {logits.shape[1]} to {args.class_num} classes"
                    )
                    warned = True
                logits = logits[:, : args.class_num]
            logits_sum[indices.numpy()] += logits.numpy().astype("float64")
    return logits_sum / max(1, len(transforms)), labels


def safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype="float64"),
        where=denominator != 0,
    )


def compute_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, class_num: int):
    matrix = np.zeros((class_num, class_num), dtype=np.int64)
    for true_label, pred_label in zip(y_true, y_pred):
        matrix[int(true_label), int(pred_label)] += 1
    return matrix


def summarize_predictions(logits: np.ndarray, y_true: np.ndarray, class_num: int):
    probabilities = softmax_np(logits)
    y_pred = np.argmax(probabilities, axis=1)
    confidence = probabilities[np.arange(len(probabilities)), y_pred]

    topk = min(3, class_num)
    topk_pred = np.argsort(logits, axis=1)[:, -topk:]
    top3_accuracy = float(np.mean(np.any(topk_pred == y_true[:, None], axis=1)))

    confusion = compute_confusion_matrix(y_true, y_pred, class_num)
    tp = np.diag(confusion).astype("float64")
    support = confusion.sum(axis=1).astype("float64")
    predicted = confusion.sum(axis=0).astype("float64")

    precision = safe_divide(tp, predicted)
    recall = safe_divide(tp, support)
    f1 = safe_divide(2.0 * precision * recall, precision + recall)

    total = float(confusion.sum())
    accuracy = float(tp.sum() / total) if total else 0.0
    summary = {
        "num_samples": int(total),
        "accuracy": accuracy,
        "top3_accuracy": top3_accuracy,
        "macro_precision": float(precision.mean()) if len(precision) else 0.0,
        "macro_recall": float(recall.mean()) if len(recall) else 0.0,
        "macro_f1": float(f1.mean()) if len(f1) else 0.0,
    }

    class_rows = []
    for class_id in range(class_num):
        class_rows.append(
            {
                "class_id": class_id,
                "support": int(support[class_id]),
                "tp": int(tp[class_id]),
                "predicted": int(predicted[class_id]),
                "precision": float(precision[class_id]),
                "recall": float(recall[class_id]),
                "f1": float(f1[class_id]),
                "class_accuracy": float(recall[class_id]),
            }
        )

    return y_pred, confidence, confusion, class_rows, summary


def write_predictions_csv(
    path: Path,
    samples: list[tuple[str, Path, int | None]],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    confidence: np.ndarray,
    model_name: str,
):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "true_label", "pred_label", "confidence", "model_name"])
        for (rel_path, _, _), true_label, pred_label, conf in zip(
            samples, y_true, y_pred, confidence
        ):
            writer.writerow(
                [
                    Path(rel_path).name,
                    int(true_label),
                    int(pred_label),
                    f"{float(conf):.6f}",
                    model_name,
                ]
            )


def write_confusion_csv(path: Path, confusion: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["true/pred"] + [str(i) for i in range(confusion.shape[1])])
        for class_id, row in enumerate(confusion):
            writer.writerow([class_id] + [int(v) for v in row.tolist()])


def write_class_metrics_csv(path: Path, class_rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "class_id",
        "support",
        "tp",
        "predicted",
        "precision",
        "recall",
        "f1",
        "class_accuracy",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in class_rows:
            writer.writerow(row)


def write_summary_json(path: Path, summary: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


@paddle.no_grad()
def main() -> None:
    args = parse_args()
    if args.device == "gpu" and not paddle.device.is_compiled_with_cuda():
        raise RuntimeError("Paddle was not compiled with CUDA. Use --device cpu.")
    paddle.set_device(args.device)

    weight_specs = parse_weight_specs(args.weights)
    transforms = build_tta_transforms(args.image_size, args.tta)
    model_name = model_tag(weight_specs)

    if args.eval_list:
        samples = collect_samples(args, args.eval_list, with_labels=True)
        ensemble_logits = np.zeros((len(samples), args.class_num), dtype="float64")
        y_true = None
        for model_index, (single_model_name, weight_path) in enumerate(
            weight_specs, start=1
        ):
            print(
                f"Model {model_index}/{len(weight_specs)}: {single_model_name} <- {weight_path}"
            )
            model = build_model(single_model_name, args.class_num, weight_path)
            logits, labels = aggregate_logits(
                model, samples, args, transforms, with_labels=True
            )
            ensemble_logits += logits
            if y_true is None:
                y_true = labels
            elif not np.array_equal(y_true, labels):
                raise ValueError("Validation label order mismatch across models.")
            del model
            if args.device == "gpu":
                paddle.device.cuda.empty_cache()

        ensemble_logits /= max(1, len(weight_specs))
        if y_true is None:
            raise RuntimeError("No validation labels loaded.")

        y_pred, confidence, confusion, class_rows, summary = summarize_predictions(
            ensemble_logits, y_true, args.class_num
        )

        predictions_path = (
            Path(args.predictions_output)
            if args.predictions_output
            else Path("val_predictions.csv")
        )
        metrics_path = (
            Path(args.metrics_output) if args.metrics_output else Path("val_metrics.json")
        )
        confusion_path = (
            Path(args.confusion_output)
            if args.confusion_output
            else Path("confusion_matrix.csv")
        )
        class_metrics_path = (
            Path(args.class_metrics_output)
            if args.class_metrics_output
            else Path("class_metrics.csv")
        )

        write_predictions_csv(
            predictions_path, samples, y_true, y_pred, confidence, model_name
        )
        write_confusion_csv(confusion_path, confusion)
        write_class_metrics_csv(class_metrics_path, class_rows)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            json.dumps(
                {
                    "model_name": model_name,
                    "weights": [f"{name}={path}" for name, path in weight_specs],
                    "tta": args.tta,
                    "image_size": args.image_size,
                    "class_num": args.class_num,
                    **summary,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"Eval accuracy {summary['accuracy']:.4f} "
            f"top3 {summary['top3_accuracy']:.4f} "
            f"macro_f1 {summary['macro_f1']:.4f}"
        )
        print(f"Wrote predictions: {predictions_path}")
        print(f"Wrote metrics: {metrics_path}")
        print(f"Wrote confusion matrix: {confusion_path}")
        print(f"Wrote class metrics: {class_metrics_path}")
        return

    samples = collect_samples(args, args.test_list, with_labels=False)
    ensemble_logits = np.zeros((len(samples), args.class_num), dtype="float64")
    for model_index, (single_model_name, weight_path) in enumerate(
        weight_specs, start=1
    ):
        print(f"Model {model_index}/{len(weight_specs)}: {single_model_name} <- {weight_path}")
        model = build_model(single_model_name, args.class_num, weight_path)
        logits, _ = aggregate_logits(model, samples, args, transforms, with_labels=False)
        ensemble_logits += logits
        del model
        if args.device == "gpu":
            paddle.device.cuda.empty_cache()

    ensemble_logits /= max(1, len(weight_specs))
    labels = np.argmax(ensemble_logits, axis=1)
    rows = [(Path(rel_path).name, int(label)) for (rel_path, _, _), label in zip(samples, labels)]

    with Path(args.output).open("w", encoding="utf-8", newline="") as f:
        for filename, label in rows:
            f.write(f"{filename},{label}\n")
    print(f"Wrote {args.output}: {len(rows)} rows")


if __name__ == "__main__":
    main()
