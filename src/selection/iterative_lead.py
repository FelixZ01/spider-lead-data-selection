#!/usr/bin/env python3
"""Utilities for a small, transparent LEAD-style Spider experiment.

This module intentionally implements a computationally feasible adaptation,
not a faithful reproduction of LEAD.  Difficulty is approximated with model
target loss, Spider database IDs act as task groups, and utility changes are
measured by rescoring rather than approximated from gradients.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any


def allocate_evenly(total: int, parts: int) -> list[int]:
    """Split an integer budget across rounds without changing the total."""
    if total < 1:
        raise ValueError("total must be positive")
    if parts < 1:
        raise ValueError("parts must be positive")
    if parts > total:
        raise ValueError("parts cannot exceed total")
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def assign_quantile_clusters(
    rows: list[dict[str, Any]], n_clusters: int, score_key: str
) -> dict[str, int]:
    """Assign near-equal difficulty clusters ordered from easy to hard."""
    if n_clusters < 1:
        raise ValueError("n_clusters must be positive")
    ordered = sorted(rows, key=lambda row: (float(row[score_key]), row["id"]))
    total = len(ordered)
    if total < n_clusters:
        raise ValueError("n_clusters cannot exceed the number of rows")
    return {
        row["id"]: min(n_clusters - 1, index * n_clusters // total)
        for index, row in enumerate(ordered)
    }


def exp3_probabilities(weights: list[float], gamma: float) -> list[float]:
    if not weights or any(weight <= 0 for weight in weights):
        raise ValueError("EXP3 weights must be positive")
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1]")
    total = sum(weights)
    arms = len(weights)
    return [
        (1.0 - gamma) * weight / total + gamma / arms for weight in weights
    ]


def choose_arm(
    probabilities: list[float], eligible: list[bool], rng: random.Random
) -> int:
    """Sample an eligible EXP3 arm after renormalising its probability."""
    available = [index for index, allowed in enumerate(eligible) if allowed]
    if not available:
        raise ValueError("No eligible MAB arm remains")
    mass = sum(probabilities[index] for index in available)
    threshold = rng.random() * mass
    cumulative = 0.0
    for index in available:
        cumulative += probabilities[index]
        if cumulative >= threshold:
            return index
    return available[-1]


def update_exp3(
    weights: list[float], arm: int, reward: float, probability: float, gamma: float
) -> list[float]:
    """Return EXP3 weights after one bounded reward update."""
    if not -1 <= reward <= 1:
        raise ValueError("reward must be normalised to [-1, 1]")
    if probability <= 0:
        raise ValueError("chosen-arm probability must be positive")
    updated = list(weights)
    updated[arm] *= math.exp(gamma * reward / (len(weights) * probability))
    return updated


def observed_idu_proxy(
    current_loss: float,
    previous_loss: float,
    previous_utility: float,
    smoothing: float,
) -> float:
    """Eq. 6-style utility using an observed finite-difference loss change.

    Cross-entropy is non-negative, so the linearly predicted next loss is
    clipped at zero.  Without this boundary, a large first-round loss drop can
    produce a negative utility and invert the IDU-reduction reward even when
    training lowers the loss again in the next round.
    """
    if not 0 <= smoothing < 1:
        raise ValueError("smoothing must be in [0, 1)")
    observed_change = current_loss - previous_loss
    predicted_next_loss = max(0.0, current_loss + observed_change)
    return (1.0 - smoothing) * predicted_next_loss + smoothing * previous_utility


def training_gradient_idu_proxy(
    training_loss: float,
    predicted_loss_change: float,
    previous_utility: float,
    smoothing: float,
) -> float:
    """Update IDU from loss and a first-order training-time gradient estimate.

    ``predicted_loss_change`` is the inner product between the current sample
    gradient and the optimizer parameter update for a tracked parameter subset.
    This quantity is collected during the ordinary backward/update pass, so the
    update does not require rescoring the candidate pool after each round.
    """
    if not 0 <= smoothing < 1:
        raise ValueError("smoothing must be in [0, 1)")
    predicted_next_loss = max(0.0, training_loss + predicted_loss_change)
    return (1.0 - smoothing) * predicted_next_loss + smoothing * previous_utility


def proportional_task_select(
    rows: list[dict[str, Any]], budget: int, utility_key: str
) -> list[dict[str, Any]]:
    """Allocate budget proportionally across database IDs, then take top utility."""
    if not 0 < budget <= len(rows):
        raise ValueError("budget must be between 1 and the number of rows")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["db_id"]].append(row)
    for group_rows in groups.values():
        group_rows.sort(key=lambda row: (-float(row[utility_key]), row["id"]))

    total = len(rows)
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for db_id, group_rows in groups.items():
        exact = budget * len(group_rows) / total
        quota = min(len(group_rows), int(math.floor(exact)))
        quotas[db_id] = quota
        remainders.append((exact - quota, db_id))

    left = budget - sum(quotas.values())
    for _, db_id in sorted(remainders, key=lambda item: (-item[0], item[1])):
        if left == 0:
            break
        if quotas[db_id] < len(groups[db_id]):
            quotas[db_id] += 1
            left -= 1

    selected = [
        row
        for db_id, quota in quotas.items()
        for row in groups[db_id][:quota]
    ]
    selected_ids = {row["id"] for row in selected}
    if len(selected) < budget:
        remainder_rows = sorted(
            (row for row in rows if row["id"] not in selected_ids),
            key=lambda row: (-float(row[utility_key]), row["id"]),
        )
        selected.extend(remainder_rows[: budget - len(selected)])
    return sorted(selected, key=lambda row: (-float(row[utility_key]), row["id"]))
