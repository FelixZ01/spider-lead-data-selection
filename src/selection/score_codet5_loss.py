#!/usr/bin/env python3
"""Score Spider examples by pretrained CodeT5 target-token cross entropy."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as functional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


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
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics-output", required=True, type=Path)
    parser.add_argument("--model", default="Salesforce/codet5-small")
    parser.add_argument("--pool-size", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-source-length", type=int, default=384)
    parser.add_argument("--max-target-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input)
    random.Random(args.seed).shuffle(rows)
    rows = rows[: args.pool_size]
    device = choose_device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    model.eval()
    started = time.perf_counter()

    for offset in range(0, len(rows), args.batch_size):
        batch_rows = rows[offset : offset + args.batch_size]
        inputs = tokenizer(
            [row["input_text"] for row in batch_rows],
            padding=True,
            truncation=True,
            max_length=args.max_source_length,
            return_tensors="pt",
        ).to(device)
        targets = tokenizer(
            text_target=[row["target_sql"] for row in batch_rows],
            padding=True,
            truncation=True,
            max_length=args.max_target_length,
            return_tensors="pt",
        )["input_ids"].to(device)
        labels = targets.clone()
        labels[labels == tokenizer.pad_token_id] = -100
        with torch.no_grad():
            logits = model(**inputs, labels=labels).logits
        token_losses = functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]),
            labels.reshape(-1),
            ignore_index=-100,
            reduction="none",
        ).reshape(labels.shape)
        valid_tokens = (labels != -100).sum(dim=1).clamp_min(1)
        example_losses = token_losses.sum(dim=1) / valid_tokens
        for row, loss in zip(batch_rows, example_losses.detach().cpu().tolist()):
            row["pretrained_target_loss"] = loss
        completed = min(offset + args.batch_size, len(rows))
        if completed % 100 == 0 or completed == len(rows):
            print(f"Scored {completed}/{len(rows)}")

    elapsed = time.perf_counter() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    losses = [row["pretrained_target_loss"] for row in rows]
    metrics = {
        "model": args.model,
        "device": str(device),
        "pool_size": len(rows),
        "database_count": len({row["db_id"] for row in rows}),
        "mean_pretrained_target_loss": sum(losses) / len(losses),
        "min_pretrained_target_loss": min(losses),
        "max_pretrained_target_loss": max(losses),
        "scoring_seconds": elapsed,
        "seed": args.seed,
    }
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
