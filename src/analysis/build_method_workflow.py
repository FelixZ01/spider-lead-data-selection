#!/usr/bin/env python3
"""Create the method workflow figure for the final Spider report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Spider_LEAD_Method_Workflow.png"

NAVY = "#183153"
BLUE = "#2455A4"
LIGHT_BLUE = "#EAF1FA"
GREEN = "#1F7A5A"
LIGHT_GREEN = "#E8F5EF"
ORANGE = "#B45F06"
LIGHT_ORANGE = "#FFF2DF"
GREY = "#5E6B7A"
LIGHT_GREY = "#F3F5F8"


def box(ax, x, y, w, h, text, face, edge, size=10.5, weight="normal"):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.35,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=size,
        color=NAVY,
        weight=weight,
        linespacing=1.25,
    )


def arrow(ax, start, end, color=GREY, curve=0.0, width=1.5):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=width,
            color=color,
            connectionstyle=f"arc3,rad={curve}",
        )
    )


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 7.8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "Dynamic gradient LEAD adaptation for Spider Text-to-SQL",
        ha="center",
        va="center",
        fontsize=17,
        color=NAVY,
        weight="bold",
    )

    box(ax, 0.025, 0.67, 0.18, 0.16, "Spider candidate pool\n1,000 training examples", LIGHT_BLUE, BLUE, weight="bold")
    box(ax, 0.025, 0.43, 0.18, 0.16, "CodeT5-small\ninitial target-token loss", LIGHT_BLUE, BLUE)
    box(ax, 0.025, 0.19, 0.18, 0.16, "Offline groups\nloss-quantile difficulty\n+ database task groups", LIGHT_BLUE, BLUE)
    arrow(ax, (0.115, 0.67), (0.115, 0.59), color=BLUE)
    arrow(ax, (0.115, 0.43), (0.115, 0.35), color=BLUE)
    ax.text(0.115, 0.87, "Offline preparation", ha="center", fontsize=12, color=BLUE, weight="bold")
    ax.text(0.55, 0.87, "Five-round dynamic loop", ha="center", fontsize=12, color=GREEN, weight="bold")

    steps = [
        (0.27, 0.68, "1  EXP3 chooses\na difficulty arm"),
        (0.48, 0.68, "2  Select 100\nhigh-utility examples"),
        (0.69, 0.68, "3  Cumulative replay\ntraining on selected union"),
        (0.69, 0.38, "4  Collect training-time\ngradient/update signal"),
        (0.48, 0.38, "5  Update smoothed IDU\nand bounded reward"),
    ]
    for x, y, text in steps:
        box(ax, x, y, 0.17, 0.14, text, LIGHT_GREEN, GREEN, size=10.2, weight="bold" if text.startswith("1") else "normal")
    arrow(ax, (0.205, 0.27), (0.27, 0.75), color=GREEN, curve=-0.10)
    arrow(ax, (0.44, 0.75), (0.48, 0.75), color=GREEN)
    arrow(ax, (0.65, 0.75), (0.69, 0.75), color=GREEN)
    arrow(ax, (0.775, 0.68), (0.775, 0.52), color=GREEN)
    arrow(ax, (0.69, 0.45), (0.65, 0.45), color=GREEN)
    arrow(ax, (0.48, 0.45), (0.355, 0.68), color=GREEN, curve=-0.28)

    box(
        ax,
        0.27,
        0.15,
        0.59,
        0.13,
        "IDU update:  u_i(r) = (1-beta) max[0, L_i + g_i^T dtheta] + beta u_i(r-1)\n"
        "EXP3 reward:  tanh(mean[u_before - u_after] / scale)",
        LIGHT_ORANGE,
        ORANGE,
        size=10.2,
    )

    box(ax, 0.875, 0.67, 0.105, 0.15, "Final\ncheckpoint", LIGHT_GREY, GREY, size=10.5, weight="bold")
    box(ax, 0.875, 0.43, 0.105, 0.15, "Spider dev\n1,034 examples", LIGHT_GREY, GREY, size=10.0)
    box(ax, 0.875, 0.19, 0.105, 0.15, "Official EM\n+ end-to-end time", LIGHT_GREY, GREY, size=10.0)
    arrow(ax, (0.86, 0.75), (0.875, 0.75), color=GREY)
    arrow(ax, (0.9275, 0.67), (0.9275, 0.58), color=GREY)
    arrow(ax, (0.9275, 0.43), (0.9275, 0.34), color=GREY)

    ax.text(
        0.5,
        0.075,
        "Fixed budget: 500 unique examples | Fixed training budget: 1,500 optimizer steps | Five seeds",
        ha="center",
        fontsize=10.2,
        color=NAVY,
        weight="bold",
    )
    ax.text(
        0.5,
        0.035,
        "Matched controls: Random | static uncertainty | observed-loss IDU | balanced-cluster replay",
        ha="center",
        fontsize=9.6,
        color=GREY,
    )

    fig.savefig(OUTPUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
