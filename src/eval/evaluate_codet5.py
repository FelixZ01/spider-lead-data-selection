#!/usr/bin/env python3
"""Generate SQL with a local CodeT5 checkpoint and report smoke-test metrics."""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().rstrip(";")).lower()


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
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--eval-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-samples", type=int, default=5)
    parser.add_argument("--max-source-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-strategy", choices=("random", "head"), default="random")
    parser.add_argument("--quiet", action="store_true", help="Do not print every prediction")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.eval_file)
    if args.sample_strategy == "random":
        random.Random(args.seed).shuffle(rows)
    rows = rows[: args.max_samples]
    device = choose_device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_dir).to(device)
    model.eval()
    predictions: list[dict[str, Any]] = []
    started = time.perf_counter()
    for row in rows:
        batch = tokenizer(
            row["input_text"],
            max_length=args.max_source_length,
            truncation=True,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            generated = model.generate(**batch, max_new_tokens=args.max_new_tokens, num_beams=1)
        prediction = tokenizer.decode(generated[0], skip_special_tokens=True)
        exact = normalize_sql(prediction) == normalize_sql(row["target_sql"])
        predictions.append({**row, "prediction": prediction, "normalized_exact_match": exact})
        if not args.quiet:
            print(f"{row['id']}: {prediction}")
    elapsed = time.perf_counter() - started
    exact_count = sum(row["normalized_exact_match"] for row in predictions)
    metrics = {
        "device": str(device),
        "eval_samples": len(predictions),
        "normalized_exact_matches": exact_count,
        "normalized_exact_match": exact_count / len(predictions) if predictions else 0.0,
        "generation_seconds": elapsed,
        "sample_strategy": args.sample_strategy,
        "seed": args.seed,
        "database_count": len({row["db_id"] for row in predictions}),
        "note": "Diagnostic normalized string match; not official Spider execution accuracy.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output_dir / "eval_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
