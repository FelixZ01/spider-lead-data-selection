#!/usr/bin/env python3
"""Generate SQL and write the JSON format expected by official BIRD EX evaluation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoModelForCausalLM, AutoTokenizer


SEPARATOR = "\t----- bird -----\t"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def clean_sql(text: str) -> str:
    """Remove common chat/code-fence wrappers while preserving the SQL."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    for marker in ("SQL:", "sql:"):
        if text.startswith(marker):
            text = text[len(marker) :].strip()
    return text.rstrip(";").strip() + ";"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--adapter", default=None, help="Optional saved LoRA adapter directory")
    parser.add_argument("--data-mode", default="dev")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input)
    if args.max_samples is not None:
        rows = rows[: args.max_samples]

    model_path = args.adapter or args.model
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    if args.adapter:
        model = AutoPeftModelForCausalLM.from_pretrained(
            args.adapter, torch_dtype=torch.bfloat16, device_map="auto"
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
        )
    model.eval()

    official_predictions: dict[str, str] = {}
    detailed_predictions: list[dict] = []
    for index, row in enumerate(rows):
        messages = row["messages"][:-1] if row["messages"][-1]["role"] == "assistant" else row["messages"]
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_tensors="pt",
        ).to(model.device)
        with torch.inference_mode():
            generated = model.generate(
                encoded,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        sql = clean_sql(tokenizer.decode(generated[0, encoded.shape[-1] :], skip_special_tokens=True))
        db_id = row["db_id"]
        official_predictions[str(index)] = f"{sql}{SEPARATOR}{db_id}"
        detailed_predictions.append({"index": index, "id": row.get("id"), "db_id": db_id, "sql": sql})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    official_path = args.output_dir / f"predict_{args.data_mode}.json"
    official_path.write_text(json.dumps(official_predictions, indent=2), encoding="utf-8")
    with (args.output_dir / f"predict_{args.data_mode}_details.jsonl").open("w", encoding="utf-8") as handle:
        for row in detailed_predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Generated {len(rows)} predictions -> {official_path}")


if __name__ == "__main__":
    main()
