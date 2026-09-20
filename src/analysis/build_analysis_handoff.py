#!/usr/bin/env python3
"""Build a concise, evidence-bounded handoff for external analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DISPLAY_NAMES = {
    "random": "Random",
    "uncertainty": "Uncertainty",
    "uncertainty_schema_diverse": "Uncertainty + schema diversity",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    lines = [
        "# Spider Text-to-SQL Experiment: Analysis Handoff",
        "",
        "## Objective",
        "",
        "Evaluate whether a lightweight schema-diversity constraint improves "
        "static uncertainty-based training-data selection for a Mac-feasible "
        "CodeT5-small Text-to-SQL pipeline.",
        "",
        "## Current stage",
        "",
        f"- Completed full Spider development-set evaluation: "
        f"{len(metrics['seeds'])} training seeds x 3 methods x "
        f"{metrics['development_examples']} examples.",
        "- Training pool: 1,000 examples.",
        "- Equal selection budget: 500 examples per method.",
        "- Training: CodeT5-small for 3 epochs on Apple MPS.",
        "- Primary reported metric: official Spider exact match.",
        "",
        "## Results",
        "",
        "| Method | Per-seed exact match | Mean | Sample SD | Gain vs random |",
        "|---|---:|---:|---:|---:|",
    ]

    for method, values in metrics["methods"].items():
        runs = ", ".join(
            f"{run['official_spider_exact_match'] * 100:.1f}%"
            for run in values["runs"]
        )
        aggregate = values["official_spider_exact_match"]
        lines.append(
            f"| {DISPLAY_NAMES[method]} | {runs} | "
            f"{aggregate['mean'] * 100:.2f}% | "
            f"{aggregate['sample_std'] * 100:.2f} pp | "
            f"{values['absolute_gain_over_random'] * 100:+.2f} pp |"
        )

    lines.extend(
        [
            "",
            "## Evidence boundaries",
            "",
            f"- {metrics['metric_boundary']}",
            f"- {metrics['method_boundary']}",
            "- These experiments use Spider and CodeT5-small, not the planned "
            "BIRD + Qwen3 extension.",
            "- With only a small number of seeds, the result should be treated "
            "as promising experimental evidence rather than a final claim.",
            "",
            "## Please analyse",
            "",
            "1. Is the schema-diversity improvement consistent and practically meaningful?",
            "2. What statistical summary is defensible with the available seeds?",
            "3. Which ablation should be run next to isolate the contribution of "
            "schema diversity from uncertainty scoring?",
            "4. What are the main threats to validity in the current design?",
            "5. Recommend one compact results table, one figure, and a report structure.",
            "6. Suggest the smallest credible extension toward BIRD + Qwen3 once GPU "
            "resources become available.",
            "",
            "Do not describe the selector as an official LEAD reproduction and do not "
            "reinterpret exact match as execution accuracy.",
            "",
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
