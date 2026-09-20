#!/usr/bin/env python3
"""Fine-tune CodeT5 on a small Spider JSONL split, including Apple MPS."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq


class SpiderDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], tokenizer: Any, max_source: int, max_target: int):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_source = max_source
        self.max_target = max_target

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        source = self.tokenizer(
            row["input_text"], max_length=self.max_source, truncation=True
        )
        target = self.tokenizer(
            text_target=row["target_sql"], max_length=self.max_target, truncation=True
        )
        return {
            "input_ids": torch.tensor(source["input_ids"]),
            "attention_mask": torch.tensor(source["attention_mask"]),
            "labels": torch.tensor(target["input_ids"]),
            "example_index": index,
        }


class TrackingCollator:
    """Keep dataset indices outside the model inputs."""

    def __init__(self, base_collator: DataCollatorForSeq2Seq):
        self.base_collator = base_collator

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        indices = [int(feature.pop("example_index")) for feature in features]
        batch = self.base_collator(features)
        batch["example_index"] = torch.tensor(indices, dtype=torch.long)
        return batch


def select_gradient_parameters(
    model: torch.nn.Module, scope: str
) -> list[tuple[str, torch.nn.Parameter]]:
    """Choose the trainable parameter subset used for the gradient proxy."""
    trainable = [(name, param) for name, param in model.named_parameters() if param.requires_grad]
    if scope == "all":
        return trainable
    decoder_layers: list[tuple[int, str, torch.nn.Parameter]] = []
    pattern = re.compile(r"(?:^|\.)decoder\.block\.(\d+)\.")
    for name, param in trainable:
        match = pattern.search(name)
        if match:
            decoder_layers.append((int(match.group(1)), name, param))
    if not decoder_layers:
        raise RuntimeError("Could not identify a decoder block for gradient telemetry")
    last_layer = max(item[0] for item in decoder_layers)
    return [(name, param) for layer, name, param in decoder_layers if layer == last_layer]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def choose_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="Salesforce/codet5-small")
    parser.add_argument("--max-samples", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional optimizer-step cap used for compute-matched comparisons.",
    )
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-source-length", type=int, default=384)
    parser.add_argument("--max-target-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-strategy", choices=("random", "head"), default="random")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument(
        "--gradient-telemetry-output",
        type=Path,
        default=None,
        help=(
            "Optional JSONL output containing training-time loss and first-order "
            "gradient utility estimates for each training example."
        ),
    )
    parser.add_argument(
        "--gradient-scope",
        choices=("decoder_last", "all"),
        default="decoder_last",
        help="Parameter subset used for the first-order gradient estimate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    rows = read_jsonl(args.train_file)
    if not rows:
        raise ValueError("Training file is empty")
    if args.sample_strategy == "random":
        random.shuffle(rows)
    rows = rows[: args.max_samples]
    if args.epochs < 1:
        raise ValueError("epochs must be positive")
    if args.max_steps is not None and args.max_steps < 1:
        raise ValueError("max-steps must be positive")
    device = choose_device(args.device)
    print(f"Loading {args.model} on {device}; training rows={len(rows)}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    dataset = SpiderDataset(rows, tokenizer, args.max_source_length, args.max_target_length)
    collator = TrackingCollator(
        DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collator)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    tracked_parameters: list[tuple[str, torch.nn.Parameter]] = []
    telemetry: dict[int, dict[str, float | int]] = {}
    if args.gradient_telemetry_output is not None:
        if args.batch_size != 1:
            raise ValueError("gradient telemetry currently requires --batch-size 1")
        tracked_parameters = select_gradient_parameters(model, args.gradient_scope)
        print(
            "Gradient telemetry scope="
            f"{args.gradient_scope}; tensors={len(tracked_parameters)}; "
            f"parameters={sum(param.numel() for _, param in tracked_parameters)}"
        )

    started = time.perf_counter()
    losses: list[float] = []
    model.train()
    effective_epochs = args.epochs
    if args.max_steps is not None:
        effective_epochs = max(effective_epochs, math.ceil(args.max_steps / len(loader)))
    for epoch in range(effective_epochs):
        for step, batch in enumerate(loader, start=1):
            example_indices = batch.pop("example_index").tolist()
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()

            gradient_norm_squared = 0.0
            parameter_snapshots: list[torch.Tensor] = []
            if tracked_parameters:
                for _, param in tracked_parameters:
                    if param.grad is not None:
                        gradient_norm_squared += float(
                            torch.sum(param.grad.detach().float() ** 2).cpu()
                        )
                    parameter_snapshots.append(param.detach().clone())
            optimizer.step()

            predicted_loss_change = 0.0
            if tracked_parameters:
                with torch.no_grad():
                    for (_, param), before in zip(
                        tracked_parameters, parameter_snapshots
                    ):
                        if param.grad is not None:
                            predicted_loss_change += float(
                                torch.sum(
                                    param.grad.detach().float()
                                    * (param.detach().float() - before.float())
                                ).cpu()
                            )
                example_index = int(example_indices[0])
                stats = telemetry.setdefault(
                    example_index,
                    {
                        "observations": 0,
                        "loss_sum": 0.0,
                        "gradient_norm_squared_sum": 0.0,
                        "predicted_loss_change_sum": 0.0,
                    },
                )
                stats["observations"] = int(stats["observations"]) + 1
                stats["loss_sum"] = float(stats["loss_sum"]) + float(loss.detach().cpu())
                stats["gradient_norm_squared_sum"] = (
                    float(stats["gradient_norm_squared_sum"]) + gradient_norm_squared
                )
                stats["predicted_loss_change_sum"] = (
                    float(stats["predicted_loss_change_sum"]) + predicted_loss_change
                )
            losses.append(float(loss.detach().cpu()))
            if step == 1 or step % args.log_every == 0 or step == len(loader):
                print(f"epoch={epoch + 1} step={step}/{len(loader)} loss={losses[-1]:.4f}")
            if args.max_steps is not None and len(losses) >= args.max_steps:
                break
        if args.max_steps is not None and len(losses) >= args.max_steps:
            break

    elapsed = time.perf_counter() - started
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    if args.gradient_telemetry_output is not None:
        args.gradient_telemetry_output.parent.mkdir(parents=True, exist_ok=True)
        with args.gradient_telemetry_output.open("w", encoding="utf-8") as handle:
            for example_index in sorted(telemetry):
                stats = telemetry[example_index]
                observations = int(stats["observations"])
                row = rows[example_index]
                handle.write(
                    json.dumps(
                        {
                            "id": row["id"],
                            "db_id": row["db_id"],
                            "observations": observations,
                            "mean_training_loss": float(stats["loss_sum"]) / observations,
                            "mean_gradient_norm_squared": float(
                                stats["gradient_norm_squared_sum"]
                            )
                            / observations,
                            "mean_predicted_loss_change": float(
                                stats["predicted_loss_change_sum"]
                            )
                            / observations,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    metrics = {
        "model": args.model,
        "device": str(device),
        "train_samples": len(rows),
        "epochs": args.epochs,
        "effective_epochs": effective_epochs,
        "max_steps": args.max_steps,
        "steps": len(losses),
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "mean_loss": sum(losses) / len(losses),
        "train_seconds": elapsed,
        "seed": args.seed,
        "sample_strategy": args.sample_strategy,
        "database_count": len({row["db_id"] for row in rows}),
        "gradient_telemetry_output": (
            str(args.gradient_telemetry_output)
            if args.gradient_telemetry_output is not None
            else None
        ),
        "gradient_scope": args.gradient_scope if tracked_parameters else None,
        "gradient_parameter_count": (
            sum(param.numel() for _, param in tracked_parameters)
            if tracked_parameters
            else 0
        ),
    }
    (args.output_dir / "train_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
