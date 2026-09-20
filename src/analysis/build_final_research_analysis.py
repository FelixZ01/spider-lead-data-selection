#!/usr/bin/env python3
"""Build the consolidated statistical and error analysis for the Spider study."""

from __future__ import annotations

import csv
import itertools
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


SEEDS = [11, 42, 73, 101, 202]
DIFFICULTIES = ["easy", "medium", "hard", "extra", "all"]
COMPONENTS = [
    "select",
    "select(no AGG)",
    "where",
    "where(no OP)",
    "group(no Having)",
    "group",
    "order",
    "and/or",
    "IUEN",
    "keywords",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def official_breakdown(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"^exact match\s+(.+)$", text, flags=re.MULTILINE)
    if not matches:
        raise ValueError(f"Could not find exact-match row in {path}")
    values = [float(value) for value in matches[-1].split()]
    if len(values) != len(DIFFICULTIES):
        raise ValueError(f"Unexpected exact-match row in {path}: {matches[-1]}")
    return dict(zip(DIFFICULTIES, values))


def official_component_f1(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    marker = "---------------------- PARTIAL MATCHING F1 --------------------------"
    if marker not in text:
        raise ValueError(f"Could not find partial-matching F1 section in {path}")
    section = text.rsplit(marker, maxsplit=1)[1]
    result = {}
    for line in section.splitlines():
        for component in COMPONENTS:
            if line.startswith(component) and (
                len(line) == len(component) or line[len(component)].isspace()
            ):
                values = line[len(component):].split()
                if len(values) == len(DIFFICULTIES):
                    result[component] = float(values[-1])
                break
    if set(result) != set(COMPONENTS):
        missing = sorted(set(COMPONENTS) - set(result))
        raise ValueError(f"Missing F1 components in {path}: {missing}")
    return result


def aggregate(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def paired_summary(left: list[float], right: list[float]) -> dict:
    differences = [a - b for a, b in zip(left, right)]
    mean_difference = statistics.mean(differences)
    sample_std = statistics.stdev(differences) if len(differences) > 1 else 0.0
    # t_(0.975, 4) for the fixed five-seed design.
    half_width = 2.776 * sample_std / math.sqrt(len(differences))
    observed = abs(mean_difference)
    sign_flip_means = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(differences)):
        sign_flip_means.append(abs(statistics.mean(d * s for d, s in zip(differences, signs))))
    p_value = sum(value >= observed - 1e-12 for value in sign_flip_means) / len(sign_flip_means)
    return {
        "paired_differences": differences,
        "mean_difference": mean_difference,
        "sample_std_of_difference": sample_std,
        "t_interval_95": [mean_difference - half_width, mean_difference + half_width],
        "exact_sign_flip_p_value": p_value,
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "interpretation_boundary": (
            "Descriptive paired analysis over five seeds. The interval is wide and the "
            "exact test has low power, so it does not establish statistical superiority."
        ),
    }


def method_rows(root: Path) -> dict[str, dict]:
    required = read_json(root / "results/spider_required_q1_q3/metrics.json")
    sources = {
        "Full Data": required["methods"]["full_data"],
        "Random": required["methods"]["random"],
        "Two-round Iterative": required["methods"]["iterative_lead"],
        "Five-round Full Adaptation": read_json(
            root / "results/spider_iterative_multiround_cumulative/metrics.json"
        ),
        "Five-round IDU-only": read_json(root / "results/spider_iterative_idu_only/metrics.json"),
        "Static Uncertainty": read_json(
            root / "results/spider_static_uncertainty_multiround/metrics.json"
        ),
        "Cluster-MAB Component": read_json(
            root / "results/spider_iterative_cluster_mab/metrics.json"
        ),
        "Database-quota Component": read_json(
            root / "results/spider_iterative_database_quota/metrics.json"
        ),
    }
    rows = {}
    for name, source in sources.items():
        if "aggregate" in source and "official_spider_exact_match" in source["aggregate"]:
            aggregate_data = source["aggregate"]
            runs = source["runs"]
        else:
            aggregate_data = source["aggregate"]
            runs = source["runs"]
        rows[name] = {
            "official_spider_exact_match": aggregate_data["official_spider_exact_match"],
            "end_to_end_seconds": aggregate_data["end_to_end_seconds"],
            "selected_databases": aggregate_data.get("selected_databases")
            or aggregate([float(row["selected_databases"]) for row in runs]),
            "runs": runs,
        }
    return rows


def official_difficulty_analysis(root: Path) -> dict:
    path_builders = {
        "Full Data": lambda seed: root
        / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/full_data/official/evaluation.txt",
        "Random": lambda seed: root
        / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/random/official/evaluation.txt",
        "Five-round IDU-only": lambda seed: root
        / f"outputs/spider_iterative_idu_only/seed_{seed}/final_official/evaluation.txt",
    }
    result = {}
    for name, builder in path_builders.items():
        per_seed = {seed: official_breakdown(builder(seed)) for seed in SEEDS}
        result[name] = {
            "per_seed": per_seed,
            "mean": {
                difficulty: statistics.mean(per_seed[seed][difficulty] for seed in SEEDS)
                for difficulty in DIFFICULTIES
            },
        }
    return result


def official_component_analysis(root: Path) -> dict:
    path_builders = {
        "Full Data": lambda seed: root
        / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/full_data/official/evaluation.txt",
        "Random": lambda seed: root
        / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/random/official/evaluation.txt",
        "Five-round IDU-only": lambda seed: root
        / f"outputs/spider_iterative_idu_only/seed_{seed}/final_official/evaluation.txt",
    }
    result = {}
    for name, builder in path_builders.items():
        per_seed = {seed: official_component_f1(builder(seed)) for seed in SEEDS}
        result[name] = {
            "per_seed": per_seed,
            "mean": {
                component: statistics.mean(per_seed[seed][component] for seed in SEEDS)
                for component in COMPONENTS
            },
        }
    return result


def selection_analysis(root: Path) -> dict:
    seed_rows = []
    round_accumulator: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    idu_complexity_total = Counter()
    random_complexity_total = Counter()
    for seed in SEEDS:
        idu = read_jsonl(root / f"outputs/spider_iterative_idu_only/seed_{seed}/selected_all.jsonl")
        random_rows = read_jsonl(
            root / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/random/selected.jsonl"
        )
        idu_ids = {row["id"] for row in idu}
        random_ids = {row["id"] for row in random_rows}
        idu_complexity_total.update(row["complexity"] for row in idu)
        random_complexity_total.update(row["complexity"] for row in random_rows)
        seed_rows.append({
            "seed": seed,
            "idu_databases": len({row["db_id"] for row in idu}),
            "random_databases": len({row["db_id"] for row in random_rows}),
            "selection_jaccard": len(idu_ids & random_ids) / len(idu_ids | random_ids),
        })
        for round_number in range(1, 6):
            current = [row for row in idu if int(row["round_selected"]) == round_number]
            round_accumulator[round_number]["databases"].append(len({row["db_id"] for row in current}))
            round_accumulator[round_number]["mean_idu_proxy"].append(
                statistics.mean(float(row["idu_proxy"]) for row in current)
            )
            for complexity in ("simple", "advanced", "nested"):
                round_accumulator[round_number][complexity].append(
                    sum(row["complexity"] == complexity for row in current)
                )
    return {
        "per_seed": seed_rows,
        "mean_selection_jaccard_vs_random": statistics.mean(
            row["selection_jaccard"] for row in seed_rows
        ),
        "mean_selected_databases": {
            "Five-round IDU-only": statistics.mean(row["idu_databases"] for row in seed_rows),
            "Random": statistics.mean(row["random_databases"] for row in seed_rows),
        },
        "complexity_counts_across_five_seeds": {
            "Five-round IDU-only": dict(idu_complexity_total),
            "Random": dict(random_complexity_total),
        },
        "idu_round_means": {
            str(round_number): {
                key: statistics.mean(values) for key, values in values_by_key.items()
            }
            for round_number, values_by_key in sorted(round_accumulator.items())
        },
    }


def diagnostic_disagreements(root: Path) -> dict:
    records: dict[str, dict] = {}
    for seed in SEEDS:
        paths = {
            "idu": root / f"outputs/spider_iterative_idu_only/seed_{seed}/final_eval/predictions.jsonl",
            "random": root
            / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/random/eval/predictions.jsonl",
        }
        for method, path in paths.items():
            for row in read_jsonl(path):
                item = records.setdefault(row["id"], {
                    "id": row["id"],
                    "db_id": row["db_id"],
                    "complexity": row["complexity"],
                    "question": row["question"],
                    "idu_correct_seeds": 0,
                    "random_correct_seeds": 0,
                })
                item[f"{method}_correct_seeds"] += int(bool(row["normalized_exact_match"]))
    for item in records.values():
        item["idu_minus_random_correct_seeds"] = (
            item["idu_correct_seeds"] - item["random_correct_seeds"]
        )
    ordered = list(records.values())
    idu_examples = sorted(
        (row for row in ordered if row["idu_minus_random_correct_seeds"] > 0),
        key=lambda row: (-row["idu_minus_random_correct_seeds"], row["id"]),
    )[:8]
    random_examples = sorted(
        (row for row in ordered if row["idu_minus_random_correct_seeds"] < 0),
        key=lambda row: (row["idu_minus_random_correct_seeds"], row["id"]),
    )[:8]
    return {
        "metric_boundary": (
            "These examples use normalized string exact match for diagnosis only. "
            "Official Spider exact match remains the primary reported metric."
        ),
        "idu_advantage_examples": idu_examples,
        "random_advantage_examples": random_examples,
    }


def sql_error_tags(target: str, prediction: str) -> set[str]:
    def normalise(sql: str) -> str:
        return " ".join(sql.lower().replace(";", " ").split())

    target_sql = normalise(target)
    predicted_sql = normalise(prediction)
    tags = set()
    set_ops = (" union ", " intersect ", " except ")
    if tuple(op in f" {target_sql} " for op in set_ops) != tuple(
        op in f" {predicted_sql} " for op in set_ops
    ):
        tags.add("set_operation")
    if target_sql.count(" join ") != predicted_sql.count(" join "):
        tags.add("join")
    aggregate_pattern = re.compile(r"\b(count|sum|avg|min|max)\s*\(")
    if Counter(aggregate_pattern.findall(target_sql)) != Counter(
        aggregate_pattern.findall(predicted_sql)
    ):
        tags.add("aggregation")
    clauses = {
        "filtering": " where ",
        "grouping": " group by ",
        "having": " having ",
        "ordering": " order by ",
        "limit": " limit ",
    }
    for label, clause in clauses.items():
        if (clause in f" {target_sql} ") != (clause in f" {predicted_sql} "):
            tags.add(label)
    target_select = target_sql.split(" from ", maxsplit=1)[0]
    predicted_select = predicted_sql.split(" from ", maxsplit=1)[0]
    if target_select != predicted_select:
        tags.add("projection_or_identifier")
    if not tags:
        tags.add("other_identifier_value_or_structure")
    return tags


def diagnostic_error_taxonomy(root: Path) -> dict:
    result = {}
    paths = {
        "Random": lambda seed: root
        / f"outputs/spider_required_q1_q3_baselines/seed_{seed}/random/eval/predictions.jsonl",
        "Five-round IDU-only": lambda seed: root
        / f"outputs/spider_iterative_idu_only/seed_{seed}/final_eval/predictions.jsonl",
    }
    for method, builder in paths.items():
        counts = Counter()
        incorrect = 0
        for seed in SEEDS:
            for row in read_jsonl(builder(seed)):
                if row["normalized_exact_match"]:
                    continue
                incorrect += 1
                counts.update(sql_error_tags(row["target_sql"], row["prediction"]))
        result[method] = {
            "incorrect_predictions": incorrect,
            "tag_counts": dict(counts),
            "tag_rate_per_incorrect_prediction": {
                tag: count / incorrect for tag, count in counts.items()
            },
        }
    return {
        "boundary": (
            "Heuristic multi-label taxonomy over normalized-string mismatches. "
            "It supports qualitative diagnosis but is not an official Spider metric."
        ),
        "methods": result,
    }


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def seconds(value: float) -> str:
    return f"{value:.1f} s"


def build_report(result: dict) -> str:
    methods = result["methods"]
    paired = result["paired_analysis"]
    difficulty = result["official_difficulty_breakdown"]
    components = result["official_component_f1"]
    selection = result["selection_analysis"]
    diagnostics = result["diagnostic_examples"]
    error_taxonomy = result["diagnostic_error_taxonomy"]
    lines = [
        "# Spider Data Selection: Consolidated Results and Critical Analysis",
        "",
        "## Experimental boundary",
        "",
        "All methods use Spider 1.0, CodeT5-small, a 1,000-example candidate pool, "
        "five fixed seeds, and official Spider exact match on the 1,034-example development set. "
        "Selected-data methods use a total budget of 500 examples. The five-round methods use "
        "the same cumulative training schedule and optimizer-step budget. The present methods are "
        "transparent adaptations of LEAD concepts, not a faithful reproduction of every LEAD component.",
        "",
        "## Main performance and cost comparison",
        "",
        "| Method | Official EM (mean ± SD) | End-to-end time | Selected DBs |",
        "|---|---:|---:|---:|",
    ]
    for name, row in methods.items():
        score = row["official_spider_exact_match"]
        time = row["end_to_end_seconds"]
        dbs = row.get("selected_databases")
        db_text = "—" if not dbs else f"{dbs['mean']:.1f}"
        lines.append(
            f"| {name} | {pct(score['mean'])} ± {100 * score['sample_std']:.2f} pp | "
            f"{seconds(time['mean'])} | {db_text} |"
        )
    idu = methods["Five-round IDU-only"]
    random = methods["Random"]
    full = methods["Full Data"]
    lines.extend([
        "",
        "![Performance-cost comparison](performance_cost.png)",
        "",
        "## Primary finding",
        "",
        f"Five-round IDU-only is the strongest selected-data method: {pct(idu['official_spider_exact_match']['mean'])}, "
        f"compared with {pct(random['official_spider_exact_match']['mean'])} for Random. The paired mean gain is "
        f"{100 * paired['Five-round IDU-only vs Random']['mean_difference']:.2f} percentage points, with wins in "
        f"{paired['Five-round IDU-only vs Random']['wins']} of 5 seeds. However, the 95% paired interval "
        f"[{100 * paired['Five-round IDU-only vs Random']['t_interval_95'][0]:.2f}, "
        f"{100 * paired['Five-round IDU-only vs Random']['t_interval_95'][1]:.2f}] percentage points crosses zero. "
        "This is promising but not conclusive evidence of superiority.",
        "",
        f"Full Data remains substantially stronger at {pct(full['official_spider_exact_match']['mean'])}. "
        f"IDU-only uses {100 * (1 - idu['end_to_end_seconds']['mean'] / full['end_to_end_seconds']['mean']):.1f}% "
        "less end-to-end time in this local setup, but loses "
        f"{100 * (full['official_spider_exact_match']['mean'] - idu['official_spider_exact_match']['mean']):.2f} "
        "percentage points. The current result therefore supports a cost-quality trade-off, not parity with full-data training.",
        "",
        "## What the component ablations show",
        "",
        "- Updating utility between rounds matters: IDU-only exceeds the fixed static-uncertainty control by "
        f"{100 * (idu['official_spider_exact_match']['mean'] - methods['Static Uncertainty']['official_spider_exact_match']['mean']):.2f} percentage points.",
        "- The complete five-round adaptation is weaker than IDU-only by "
        f"{100 * (idu['official_spider_exact_match']['mean'] - methods['Five-round Full Adaptation']['official_spider_exact_match']['mean']):.2f} percentage points. "
        "This indicates that adding all allocation components does not automatically help in the small Spider setting.",
        "- The cluster-MAB component is weaker than IDU-only in all five seeds, suggesting that the present two-cluster reward allocation is too coarse or unstable.",
        "- Database-quota allocation also underperforms IDU-only and covers fewer databases on average. Proportional quotas do not guarantee broader or more useful coverage.",
        "",
        "## Official difficulty breakdown",
        "",
        "| Method | Easy | Medium | Hard | Extra | All |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for name in ("Full Data", "Random", "Five-round IDU-only"):
        means = difficulty[name]["mean"]
        lines.append("| " + name + " | " + " | ".join(pct(means[key]) for key in DIFFICULTIES) + " |")
    lines.extend([
        "",
        "![Difficulty breakdown](difficulty_breakdown.png)",
        "",
        "The gain from IDU-only is not uniform across difficulty levels. This breakdown should be used to identify "
        "where iterative utility updating helps and where errors remain concentrated, rather than relying only on the overall mean.",
        "",
        "## Official SQL-component F1",
        "",
        "| Component | Full Data | Random | Five-round IDU-only | IDU − Random |",
        "|---|---:|---:|---:|---:|",
    ])
    for component in COMPONENTS:
        full_value = components["Full Data"]["mean"][component]
        random_value = components["Random"]["mean"][component]
        idu_value = components["Five-round IDU-only"]["mean"][component]
        lines.append(
            f"| {component} | {pct(full_value)} | {pct(random_value)} | {pct(idu_value)} | "
            f"{100 * (idu_value - random_value):+.2f} pp |"
        )
    lines.extend([
        "",
        "![SQL-component F1 differences](component_f1_difference.png)",
        "",
        "These official partial-match scores locate the structural sources of the overall difference. They are diagnostic "
        "component scores and should not be substituted for official exact match. IUEN is rare in this evaluation and its "
        "reported F1 is unstable when a run has no matching predictions, so the large IUEN difference should not be interpreted alone.",
        "",
        "## Selection behaviour",
        "",
        f"The mean Jaccard overlap between IDU-only and Random selections is only "
        f"{selection['mean_selection_jaccard_vs_random']:.3f}, confirming that IDU changes which examples are chosen. "
        f"IDU-only covers {selection['mean_selected_databases']['Five-round IDU-only']:.1f} databases on average, "
        f"compared with {selection['mean_selected_databases']['Random']:.1f} for Random. Its advantage therefore "
        "does not come from maximising raw database count alone; it is more consistent with repeatedly updating which remaining examples are informative.",
        "",
        "## Diagnostic examples",
        "",
        diagnostics["metric_boundary"],
        "",
        "Examples more consistently solved by IDU-only:",
        "",
    ])
    for row in diagnostics["idu_advantage_examples"][:5]:
        lines.append(
            f"- `{row['id']}` ({row['db_id']}, {row['complexity']}): "
            f"IDU {row['idu_correct_seeds']}/5 vs Random {row['random_correct_seeds']}/5 — {row['question']}"
        )
    lines.extend(["", "Examples more consistently solved by Random:", ""])
    for row in diagnostics["random_advantage_examples"][:5]:
        lines.append(
            f"- `{row['id']}` ({row['db_id']}, {row['complexity']}): "
            f"IDU {row['idu_correct_seeds']}/5 vs Random {row['random_correct_seeds']}/5 — {row['question']}"
        )
    lines.extend([
        "",
        "### Heuristic error categories",
        "",
        error_taxonomy["boundary"],
        "",
        "| Error tag | Random | Five-round IDU-only |",
        "|---|---:|---:|",
    ])
    all_tags = sorted(
        set(error_taxonomy["methods"]["Random"]["tag_counts"])
        | set(error_taxonomy["methods"]["Five-round IDU-only"]["tag_counts"])
    )
    for tag in all_tags:
        random_rate = error_taxonomy["methods"]["Random"]["tag_rate_per_incorrect_prediction"].get(tag, 0.0)
        idu_rate = error_taxonomy["methods"]["Five-round IDU-only"]["tag_rate_per_incorrect_prediction"].get(tag, 0.0)
        lines.append(f"| {tag} | {pct(random_rate)} | {pct(idu_rate)} |")
    lines.extend([
        "",
        "## Limitations and next decision",
        "",
        "1. Five seeds are enough to expose instability but not enough for a strong statistical claim.",
        "2. CodeT5-small has a large remaining gap to Full Data, especially on structurally difficult queries.",
        "3. The IDU proxy is observed loss change after training; it is an explicit practical adaptation rather than LEAD's full inference-free formulation.",
        "4. MAB and quota variants may be disadvantaged by the small pool, few rounds, and coarse grouping choices.",
        "",
        "The next priority should be manual verification of representative errors and consolidation into the mini-project report. "
        "A larger model or broader budget sweep is secondary unless additional compute becomes available.",
        "",
    ])
    return "\n".join(lines)


def write_method_csv(path: Path, methods: dict[str, dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["method", "official_em_mean", "official_em_sample_std", "end_to_end_seconds_mean", "selected_databases_mean"])
        for name, row in methods.items():
            writer.writerow([
                name,
                row["official_spider_exact_match"]["mean"],
                row["official_spider_exact_match"]["sample_std"],
                row["end_to_end_seconds"]["mean"],
                "" if not row.get("selected_databases") else row["selected_databases"]["mean"],
            ])


def write_figures(output_dir: Path, result: dict) -> None:
    cache_dir = Path("/tmp/spider_matplotlib_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = result["methods"]
    display = {
        "Full Data": "Full",
        "Random": "Random",
        "Two-round Iterative": "2-round",
        "Five-round Full Adaptation": "Full adapt.",
        "Five-round IDU-only": "IDU-only",
        "Static Uncertainty": "Static",
        "Cluster-MAB Component": "Cluster-MAB",
        "Database-quota Component": "DB quota",
    }
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    for name, label in display.items():
        row = methods[name]
        x = row["end_to_end_seconds"]["mean"] / 60.0
        y = 100.0 * row["official_spider_exact_match"]["mean"]
        ax.scatter(x, y, s=75 if name == "Five-round IDU-only" else 48)
        ax.annotate(label, (x, y), xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Mean end-to-end time (minutes)")
    ax.set_ylabel("Official Spider exact match (%)")
    ax.set_title("Performance-cost comparison")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "performance_cost.png", dpi=180)
    plt.close(fig)

    difficulty = result["official_difficulty_breakdown"]
    labels = ["Easy", "Medium", "Hard", "Extra"]
    keys = ["easy", "medium", "hard", "extra"]
    x_positions = list(range(len(keys)))
    width = 0.25
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    for offset, name in zip((-width, 0.0, width), ("Full Data", "Random", "Five-round IDU-only")):
        values = [100.0 * difficulty[name]["mean"][key] for key in keys]
        ax.bar([x + offset for x in x_positions], values, width=width, label=name)
    ax.set_xticks(x_positions, labels)
    ax.set_ylabel("Official exact match (%)")
    ax.set_title("Performance by official Spider difficulty")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "difficulty_breakdown.png", dpi=180)
    plt.close(fig)

    components = result["official_component_f1"]
    plotted_components = [component for component in COMPONENTS if component != "IUEN"]
    deltas = [
        100.0
        * (
            components["Five-round IDU-only"]["mean"][component]
            - components["Random"]["mean"][component]
        )
        for component in plotted_components
    ]
    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    colors = ["#2a9d8f" if value >= 0 else "#e76f51" for value in deltas]
    ax.barh(plotted_components, deltas, color=colors)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("IDU-only minus Random F1 (percentage points)")
    ax.set_title("Official SQL-component differences (excluding sparse IUEN)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "component_f1_difference.png", dpi=180)
    plt.close(fig)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "results/spider_final_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    methods = method_rows(root)
    score_by_method = {
        name: {int(row["seed"]): float(row["official_spider_exact_match"]) for row in data["runs"]}
        for name, data in methods.items()
    }
    idu_scores = [score_by_method["Five-round IDU-only"][seed] for seed in SEEDS]
    comparisons = {}
    for other in ("Random", "Static Uncertainty", "Five-round Full Adaptation", "Full Data"):
        comparisons[f"Five-round IDU-only vs {other}"] = paired_summary(
            idu_scores, [score_by_method[other][seed] for seed in SEEDS]
        )
    result = {
        "scope": {
            "dataset": "Spider 1.0",
            "model": "Salesforce/codet5-small",
            "candidate_pool": 1000,
            "selected_budget": 500,
            "development_examples": 1034,
            "seeds": SEEDS,
            "primary_metric": "official Spider exact match",
        },
        "methods": methods,
        "paired_analysis": comparisons,
        "official_difficulty_breakdown": official_difficulty_analysis(root),
        "official_component_f1": official_component_analysis(root),
        "selection_analysis": selection_analysis(root),
        "diagnostic_examples": diagnostic_disagreements(root),
        "diagnostic_error_taxonomy": diagnostic_error_taxonomy(root),
    }
    (output_dir / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output_dir / "REPORT.md").write_text(build_report(result), encoding="utf-8")
    write_method_csv(output_dir / "method_comparison.csv", methods)
    write_figures(output_dir, result)
    print(output_dir / "REPORT.md")


if __name__ == "__main__":
    main()
