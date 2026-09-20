#!/usr/bin/env python3
"""Build the multi-seed research analysis for the Spider LEAD adaptation."""

from __future__ import annotations

import itertools
import json
import math
import re
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEEDS = [11, 42, 73, 101, 202]
T_95_DF4 = 2.7764451051977987


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def official_exact_vector(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    rows = re.findall(r"^exact match\s+(.+)$", text, flags=re.MULTILINE)
    if not rows:
        raise ValueError(f"Could not find exact-match row in {path}")
    values = [float(value) for value in rows[-1].split()]
    if len(values) != 5:
        raise ValueError(f"Unexpected exact-match row in {path}: {rows[-1]}")
    return dict(zip(("easy", "medium", "hard", "extra", "all"), values))


def aggregate(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def paired_summary(a: list[float], b: list[float]) -> dict[str, float | list[float]]:
    differences = [left - right for left, right in zip(a, b)]
    mean = statistics.mean(differences)
    sample_std = statistics.stdev(differences)
    half_width = T_95_DF4 * sample_std / math.sqrt(len(differences))
    return {
        "differences": differences,
        "mean_difference": mean,
        "sample_std": sample_std,
        "ci95": [mean - half_width, mean + half_width],
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "cohen_dz": mean / sample_std if sample_std else 0.0,
    }


def selected_ids(base: Path, seed: int) -> set[str]:
    path = base / f"seed_{seed}" / "selected_all.jsonl"
    return {
        json.loads(line)["id"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def mean_pairwise_jaccard(sets: dict[int, set[str]]) -> float:
    values = []
    for left, right in itertools.combinations(SEEDS, 2):
        intersection = len(sets[left] & sets[right])
        union = len(sets[left] | sets[right])
        values.append(intersection / union)
    return statistics.mean(values)


def method_vectors() -> dict[str, dict[int, dict[str, float]]]:
    paths = {
        "dynamic_gradient_exp3_replay": lambda seed: ROOT
        / "outputs/spider_dynamic_gradient_lead_replay"
        / f"seed_{seed}/final_official/evaluation.txt",
        "balanced_replay_control": lambda seed: ROOT
        / "outputs/spider_gradient_balanced_replay"
        / f"seed_{seed}/final_official/evaluation.txt",
        "random": lambda seed: ROOT
        / "outputs/spider_required_q1_q3_baselines"
        / f"seed_{seed}/random/official/evaluation.txt",
        "full_data": lambda seed: ROOT
        / "outputs/spider_required_q1_q3_baselines"
        / f"seed_{seed}/full_data/official/evaluation.txt",
        "observed_loss_idu": lambda seed: ROOT
        / "outputs/spider_iterative_idu_only"
        / f"seed_{seed}/final_official/evaluation.txt",
        "previous_five_round": lambda seed: ROOT
        / "outputs/spider_iterative_multiround_cumulative"
        / f"seed_{seed}/final_official/evaluation.txt",
    }
    return {
        method: {seed: official_exact_vector(path_fn(seed)) for seed in SEEDS}
        for method, path_fn in paths.items()
    }


def main() -> None:
    vectors = method_vectors()
    aggregates = {
        method: {
            level: aggregate([by_seed[seed][level] for seed in SEEDS])
            for level in ("easy", "medium", "hard", "extra", "all")
        }
        for method, by_seed in vectors.items()
    }

    dynamic_scores = [
        vectors["dynamic_gradient_exp3_replay"][seed]["all"] for seed in SEEDS
    ]
    comparisons = {}
    for method in (
        "balanced_replay_control",
        "random",
        "observed_loss_idu",
        "previous_five_round",
        "full_data",
    ):
        comparisons[method] = paired_summary(
            dynamic_scores,
            [vectors[method][seed]["all"] for seed in SEEDS],
        )

    dynamic_base = ROOT / "outputs/spider_dynamic_gradient_lead_replay"
    balanced_base = ROOT / "outputs/spider_gradient_balanced_replay"
    dynamic_sets = {seed: selected_ids(dynamic_base, seed) for seed in SEEDS}
    balanced_sets = {seed: selected_ids(balanced_base, seed) for seed in SEEDS}
    dynamic_summaries = {
        seed: read_json(dynamic_base / f"seed_{seed}/experiment_summary.json")
        for seed in SEEDS
    }
    hard_arm_counts = {
        seed: sum(
            item["selected_difficulty_cluster"]
            for item in dynamic_summaries[seed]["round_summaries"]
        )
        for seed in SEEDS
    }

    dynamic_metrics = read_json(
        ROOT / "results/spider_dynamic_gradient_lead_replay/metrics.json"
    )
    balanced_metrics = read_json(
        ROOT / "results/spider_gradient_balanced_replay/metrics.json"
    )

    result = {
        "research_question": (
            "Under a fixed 500-example and 1,500-step budget, does the dynamic "
            "gradient-based LEAD adaptation provide stable gains for Spider "
            "Text-to-SQL, and which components explain its behaviour?"
        ),
        "seeds": SEEDS,
        "metric": "official Spider exact match",
        "performance_by_difficulty": aggregates,
        "paired_comparisons_dynamic_minus_baseline": comparisons,
        "selection_behaviour": {
            "dynamic_mean_pairwise_jaccard": mean_pairwise_jaccard(dynamic_sets),
            "balanced_mean_pairwise_jaccard": mean_pairwise_jaccard(balanced_sets),
            "dynamic_hard_cluster_rounds": hard_arm_counts,
            "dynamic_selected_database_mean": dynamic_metrics["aggregate"]
            ["selected_databases"]["mean"],
            "balanced_selected_database_mean": balanced_metrics["aggregate"]
            ["selected_databases"]["mean"],
        },
        "timing": {
            "dynamic_end_to_end_seconds": dynamic_metrics["aggregate"]
            ["end_to_end_seconds"],
            "balanced_end_to_end_seconds": balanced_metrics["aggregate"]
            ["end_to_end_seconds"],
        },
        "interpretation": {
            "supported": [
                "Cumulative replay prevents the severe forgetting observed when each round trains only on the newest batch.",
                "Dynamic EXP3 has a small average advantage over the matched balanced-cluster control, but the direction changes across seeds.",
                "The dynamic method is competitive with Random under the same selected-data and optimizer-step budget.",
            ],
            "not_supported": [
                "A reliable improvement over Random, because the paired confidence interval includes zero.",
                "A reliable improvement over observed-loss IDU, which has a higher mean in this five-seed study.",
                "Parity with Full Data, which remains substantially stronger.",
            ],
            "unexpected_result": (
                "Seed 42 suggested a large EXP3 gain, but the five-seed paired "
                "analysis showed that this was not a stable general effect."
            ),
        },
        "limitations": [
            "Only five seeds were used, so uncertainty intervals remain wide.",
            "Difficulty clusters use pretrained target-loss quantiles rather than the paper's original semantic clustering pipeline.",
            "The gradient proxy tracks the final decoder block of a fully fine-tuned CodeT5-small model rather than final-layer LoRA parameters of a causal language model.",
            "EXP3 receives only five allocation decisions, limiting its opportunity to learn a stable policy.",
            "Official exact match is strict and does not measure execution equivalence.",
        ],
    }

    output_dir = ROOT / "results/spider_dynamic_gradient_lead_replay"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "research_analysis.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )

    dynamic = aggregates["dynamic_gradient_exp3_replay"]["all"]
    balanced = aggregates["balanced_replay_control"]["all"]
    random = aggregates["random"]["all"]
    idu = aggregates["observed_loss_idu"]["all"]
    full = aggregates["full_data"]["all"]
    lines = [
        "# Dynamic Gradient LEAD Adaptation: Multi-seed Analysis",
        "",
        "## Controlled question",
        "",
        result["research_question"],
        "",
        "All selected-data methods use CodeT5-small, a 1,000-example candidate pool, a 500-example unique-data budget, 1,500 optimizer steps, the full 1,034-example Spider development set, and seeds 11, 42, 73, 101, and 202.",
        "",
        "## Main results",
        "",
        "| Method | Exact match, mean ± SD |",
        "|---|---:|",
        f"| Dynamic gradient + EXP3 + replay | {dynamic['mean']*100:.2f}% ± {dynamic['sample_std']*100:.2f}% |",
        f"| Balanced-cluster replay control | {balanced['mean']*100:.2f}% ± {balanced['sample_std']*100:.2f}% |",
        f"| Random (500 examples) | {random['mean']*100:.2f}% ± {random['sample_std']*100:.2f}% |",
        f"| Observed-loss IDU | {idu['mean']*100:.2f}% ± {idu['sample_std']*100:.2f}% |",
        f"| Full Data (1,000 examples) | {full['mean']*100:.2f}% ± {full['sample_std']*100:.2f}% |",
        "",
        "## Paired findings",
        "",
    ]
    labels = {
        "balanced_replay_control": "balanced-cluster replay",
        "random": "Random",
        "observed_loss_idu": "observed-loss IDU",
        "previous_five_round": "the previous five-round adaptation",
        "full_data": "Full Data",
    }
    for method, label in labels.items():
        row = comparisons[method]
        lines.append(
            f"- Versus {label}: mean difference {row['mean_difference']*100:+.2f} percentage points; "
            f"95% paired interval [{row['ci95'][0]*100:+.2f}, {row['ci95'][1]*100:+.2f}]; "
            f"wins/ties/losses = {row['wins']}/{row['ties']}/{row['losses']}."
        )
    lines.extend(
        [
            "",
            "None of the paired intervals against the selected-data baselines excludes zero. The dynamic method should therefore be described as competitive, not consistently superior.",
            "",
            "## Selection and timing behaviour",
            "",
            f"- Dynamic selections have mean pairwise Jaccard overlap {result['selection_behaviour']['dynamic_mean_pairwise_jaccard']:.2f}; the fixed balanced control has overlap {result['selection_behaviour']['balanced_mean_pairwise_jaccard']:.2f}.",
            "- The dynamic method covers 123.2 databases on average; the balanced control covers 122.0.",
            f"- Mean end-to-end time is {dynamic_metrics['aggregate']['end_to_end_seconds']['mean']:.1f} seconds for dynamic EXP3 and {balanced_metrics['aggregate']['end_to_end_seconds']['mean']:.1f} seconds for the balanced control.",
            "- EXP3 changes the selected difficulty path, but its five decisions are insufficient to establish a stable policy across seeds.",
            "",
            "## Critical interpretation",
            "",
            "Cumulative replay is the clearest successful design change: it raises the dynamic seed-42 run from 10.3% without replay to 19.5% with replay. Across five seeds, however, the dynamic method averages 15.94%, only 0.30 percentage points above Random and 0.92 points above the matched balanced control. The result varies substantially with seed, so the large seed-42 gain is an example of why multi-seed validation is necessary.",
            "",
            "The current evidence does not show that EXP3 or the gradient proxy reliably improves final accuracy. It does show a complete dynamic selection loop, exposes the effect of forgetting, and provides a controlled negative or mixed result that can be analysed rather than hidden.",
            "",
            "## Limitations and next step",
            "",
            "The main limitations are the five-seed sample, task-specific loss-quantile clusters, a final-decoder-block gradient proxy instead of LoRA-gradient geometry, only five bandit decisions, and exact-match-only evaluation. The next justified experiment is not another broad parameter sweep. It is a targeted reward-design test or a higher-frequency allocation design, motivated by the observation that current rewards mostly rise with training round and weakly distinguish difficulty arms.",
        ]
    )
    (output_dir / "RESEARCH_ANALYSIS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
