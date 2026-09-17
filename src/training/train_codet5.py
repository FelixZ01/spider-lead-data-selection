#!/usr/bin/env python3
"""Fine-tune CodeT5 on a small Spider JSONL split, including Apple MPS."""

from __future__ import annotations

import argparse
import json
import random
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
        }


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
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-source-length", type=int, default=384)
    parser.add_argument("--max-target-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-strategy", choices=("random", "head"), default="random")
    parser.add_argument("--device", default="auto")
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
    device = choose_device(args.device)
    print(f"Loading {args.model} on {device}; training rows={len(rows)}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    dataset = SpiderDataset(rows, tokenizer, args.max_source_length, args.max_target_length)
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collator)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    started = time.perf_counter()
    losses: list[float] = []
    model.train()
    for epoch in range(args.epochs):
        for step, batch in enumerate(loader, start=1):
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            print(f"epoch={epoch + 1} step={step}/{len(loader)} loss={losses[-1]:.4f}")

    elapsed = time.perf_counter() - started
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    metrics = {
        "model": args.model,
        "device": str(device),
        "train_samples": len(rows),
        "epochs": args.epochs,
        "steps": len(losses),
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "mean_loss": sum(losses) / len(losses),
        "train_seconds": elapsed,
        "seed": args.seed,
        "sample_strategy": args.sample_strategy,
        "database_count": len({row["db_id"] for row in rows}),
    }
    (args.output_dir / "train_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
