#!/usr/bin/env python3
"""Create the final Spider iterative-data-selection experiment report."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "results/spider_final_analysis/analysis.json"
DYNAMIC_METRICS = ROOT / "results/spider_dynamic_gradient_lead_replay/metrics.json"
DYNAMIC_ANALYSIS = ROOT / "results/spider_dynamic_gradient_lead_replay/research_analysis.json"
OUTPUT = ROOT / "Spider_LEAD_Final_Experiment_Report.pdf"
WORKFLOW_FIGURE = ROOT / "Spider_LEAD_Method_Workflow.png"
FIGURE_DIR = ROOT / "results/spider_final_analysis"

NAVY = colors.HexColor("#183153")
BLUE = colors.HexColor("#2455A4")
LIGHT_BLUE = colors.HexColor("#DCE8F7")
PALE = colors.HexColor("#F5F7FA")
GREEN = colors.HexColor("#1F7A5A")
RED = colors.HexColor("#A33A32")
GREY = colors.HexColor("#5E6B7A")
LINE = colors.HexColor("#B9C7D8")


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def pp(value: float) -> str:
    return f"{100.0 * value:+.2f} pp"


def paragraph(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=GREY,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15.5,
            leading=19,
            textColor=BLUE,
            spaceBefore=9,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=NAVY,
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.25,
            leading=13.2,
            textColor=colors.HexColor("#172033"),
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=10.4,
            textColor=GREY,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12.8,
            leftIndent=12,
            firstLineIndent=-7,
            bulletIndent=3,
            textColor=colors.HexColor("#172033"),
            spaceAfter=3,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=NAVY,
            borderColor=LIGHT_BLUE,
            borderWidth=1,
            borderPadding=8,
            backColor=colors.HexColor("#EFF5FC"),
            spaceBefore=5,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.7,
            leading=10,
            textColor=GREY,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),
    }


def table(data, widths, repeat_rows=1, font_size=7.7) -> Table:
    result = Table(data, colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size + 3),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return result


class ReportDoc(BaseDocTemplate):
    def __init__(self, filename: str, styles: dict[str, ParagraphStyle]):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=17 * mm,
            bottomMargin=17 * mm,
            title="Experiment Report - Iterative Data Selection for Spider Text-to-SQL",
            author="Zhanfei Zhang",
        )
        self.report_styles = styles
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(PageTemplate(id="report", frames=frame, onPage=self.draw_page))

    def draw_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.45)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.setFillColor(GREY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 8.5 * mm, "Spider Iterative Data Selection - Zhanfei Zhang")
        canvas.drawRightString(A4[0] - 18 * mm, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()


def add_figure(story: list, filename: str, caption: str, width_mm: float, styles: dict) -> None:
    path = Path(filename)
    if not path.is_absolute():
        path = FIGURE_DIR / path
    probe = Image(str(path))
    draw_width = width_mm * mm
    draw_height = probe.imageHeight * draw_width / probe.imageWidth
    image = Image(str(path), width=draw_width, height=draw_height)
    story.extend([image, paragraph(caption, styles["caption"])])


def build_story(
    data: dict,
    dynamic_metrics: dict,
    dynamic_analysis: dict,
    styles: dict[str, ParagraphStyle],
) -> list:
    methods = data["methods"]
    paired = data["paired_analysis"]["Five-round IDU-only vs Random"]
    difficulty = data["official_difficulty_breakdown"]
    components = data["official_component_f1"]
    selection = data["selection_analysis"]
    dynamic_performance = dynamic_analysis["performance_by_difficulty"]
    dynamic_paired = dynamic_analysis["paired_comparisons_dynamic_minus_baseline"]
    dynamic_timing = dynamic_analysis["timing"]
    dynamic_mean = dynamic_performance["dynamic_gradient_exp3_replay"]["all"]
    balanced_mean = dynamic_performance["balanced_replay_control"]["all"]
    if abs(dynamic_metrics["aggregate"]["official_spider_exact_match"]["mean"] - dynamic_mean["mean"]) > 1e-12:
        raise ValueError("Dynamic metric sources disagree")

    story = [
        Spacer(1, 18 * mm),
        paragraph("Experiment Report", styles["title"]),
        paragraph("Iterative Data Selection for Spider Text-to-SQL", styles["subtitle"]),
        paragraph("Spider 1.0 + CodeT5-small | 21 September 2026", styles["subtitle"]),
        Spacer(1, 8 * mm),
        paragraph(
            "This study investigates whether iterative model-aware data selection can improve Text-to-SQL "
            "fine-tuning under a fixed 500-example budget. It evaluates both an observed-loss IDU adaptation "
            "and a training-time gradient IDU adaptation with EXP3 and cumulative replay. All principal methods "
            "use five fixed seeds and the official Spider exact-match evaluator.",
            styles["callout"],
        ),
        paragraph("Executive summary", styles["h1"]),
        paragraph(
            "Observed-loss IDU achieved the strongest selected-data mean at <b>17.08%</b>, compared with "
            "15.64% for Random. The closer-to-LEAD training-time gradient adaptation achieved <b>15.94%</b> "
            "with EXP3 and cumulative replay. It exceeded Random in three of five seeds, but its paired 95% "
            "interval also crossed zero. Neither adaptive result supports a claim of stable superiority.",
            styles["body"],
        ),
        paragraph(
            "Full-data training remained clearly stronger at 23.02%. The dynamic gradient method required "
            "489.2 seconds end to end, 29.4% less than Full Data, while losing 7.08 percentage points. The "
            "evidence therefore demonstrates a measurable cost-quality trade-off, not full-data parity.",
            styles["body"],
        ),
        paragraph("1. Research questions", styles["h1"]),
        paragraph("Q1. Can a 500-example selected subset match or exceed training on all 1,000 candidate examples?", styles["bullet"]),
        paragraph("Q2. Does iterative model-aware selection outperform Random under the same selected-data and optimizer-step budget?", styles["bullet"]),
        paragraph("Q3. Does the iterative method improve the end-to-end performance-cost trade-off?", styles["bullet"]),
        paragraph("Q4. Does iterative selection help relative to a fixed subset, and do gradient IDU and EXP3 provide stable gains?", styles["bullet"]),
        paragraph("2. Experimental design", styles["h1"]),
    ]

    setup = [
        ["Item", "Controlled setting"],
        ["Dataset", "Spider 1.0; 1,000-example training candidate pool; full 1,034-example development set"],
        ["Model", "Salesforce CodeT5-small"],
        ["Selected-data budget", "500 examples for every selected-data method"],
        ["Seeds", "11, 42, 73, 101, 202"],
        ["Primary metric", "Official Spider exact match"],
        ["Selected-data training", "Five-round methods: 100 examples per round; cumulative union; 1,500 total optimizer steps"],
        ["Cost boundary", "Selection/scoring + training + generation + official evaluation"],
    ]
    story.extend([
        table(setup, [39 * mm, 130 * mm], font_size=7.5),
        paragraph("Fairness controls", styles["h2"]),
        paragraph(
            "Random and all iterative selected-data methods use the same 500-example budget, model, seeds, "
            "development set, and primary metric. The five-round variants also share the same cumulative "
            "training schedule and total optimizer-step budget. Full Data uses all 1,000 examples for three "
            "epochs; its larger training cost is included in the end-to-end comparison.",
            styles["body"],
        ),
        paragraph("3. Adaptation of LEAD to Spider", styles["h1"]),
        paragraph(
            "LEAD uses iterative model feedback, Instance-Level Dynamic Uncertainty (IDU), and coarse-to-fine "
            "allocation with a multi-armed bandit. This project implements a transparent, computationally "
            "manageable Spider adaptation and explicitly separates the paper-aligned components from the "
            "task-specific approximations.",
            styles["body"],
        ),
        paragraph("- Static uncertainty ranks examples once by pretrained target loss and does not update utility.", styles["bullet"]),
        paragraph("- Observed-loss IDU selects 100 examples per round, trains on the cumulative selected set, rescales utility from measured target-loss change, and then selects the next batch.", styles["bullet"]),
        paragraph("- Gradient IDU estimates first-order loss change during ordinary training from the final CodeT5 decoder block, applies historical smoothing, and avoids a separate remaining-pool rescoring pass.", styles["bullet"]),
        paragraph("- The dynamic method adds loss-quantile difficulty clusters, Spider database task groups, EXP3 allocation from bounded IDU-reduction rewards, and cumulative replay across five rounds.", styles["bullet"]),
        paragraph("- A balanced-cluster replay control keeps gradient IDU, grouping, replay, budget, and optimizer steps fixed but replaces EXP3 with the fixed schedule 0, 1, 0, 1, 0.", styles["bullet"]),
        paragraph(
            "Gradient update: u_i(r) = (1-beta) max[0, L_i + g_i^T dtheta] + beta u_i(r-1). "
            "The tracked gradient/update inner product is a first-order proxy for the next loss; cross-entropy "
            "is clipped at zero before historical smoothing.",
            styles["small"],
        ),
        paragraph("Focused hypothesis and competing explanation", styles["h2"]),
        paragraph(
            "Hypothesis: training-time gradient IDU with EXP3 will improve the performance-cost trade-off over "
            "Random and a fixed cluster schedule. Competing explanation: any gain may come from cumulative replay "
            "and repeated exposure rather than adaptive bandit allocation. The balanced replay control isolates "
            "this explanation while preserving the remaining training design.",
            styles["body"],
        ),
    ])
    add_figure(
        story,
        str(WORKFLOW_FIGURE),
        "Figure 1. Five-round dynamic gradient LEAD adaptation and matched evaluation boundary.",
        165,
        styles,
    )
    story.append(paragraph("4. Main performance and cost results", styles["h1"]))

    order = [
        "Full Data",
        "Random",
        "Two-round Iterative",
        "Five-round Full Adaptation",
        "Five-round IDU-only",
        "Static Uncertainty",
        "Cluster-MAB Component",
        "Database-quota Component",
    ]
    result_table = [["Method", "Official EM", "End-to-end", "Databases"]]
    for name in order:
        row = methods[name]
        result_table.append([
            name,
            f"{pct(row['official_spider_exact_match']['mean'])} +/- {100 * row['official_spider_exact_match']['sample_std']:.2f} pp",
            f"{row['end_to_end_seconds']['mean']:.1f} s",
            f"{row['selected_databases']['mean']:.1f}",
        ])
    result_table.extend([
        [
            "Dynamic Gradient + EXP3",
            f"{pct(dynamic_mean['mean'])} +/- {100 * dynamic_mean['sample_std']:.2f} pp",
            f"{dynamic_timing['dynamic_end_to_end_seconds']['mean']:.1f} s",
            f"{dynamic_analysis['selection_behaviour']['dynamic_selected_database_mean']:.1f}",
        ],
        [
            "Balanced Gradient Control",
            f"{pct(balanced_mean['mean'])} +/- {100 * balanced_mean['sample_std']:.2f} pp",
            f"{dynamic_timing['balanced_end_to_end_seconds']['mean']:.1f} s",
            f"{dynamic_analysis['selection_behaviour']['balanced_selected_database_mean']:.1f}",
        ],
    ])
    result_grid = table(result_table, [62 * mm, 43 * mm, 35 * mm, 29 * mm], font_size=7.25)
    result_grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#E5F4ED")),
        ("TEXTCOLOR", (0, 5), (-1, 5), GREEN),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("BACKGROUND", (0, 9), (-1, 9), colors.HexColor("#EAF1FA")),
        ("FONTNAME", (0, 9), (-1, 9), "Helvetica-Bold"),
    ]))
    story.extend([
        result_grid,
        Spacer(1, 3 * mm),
    ])
    add_figure(story, "performance_cost.png", "Figure 2. Mean official exact match against measured end-to-end time for the initial comparison set.", 150, styles)
    story.extend([
        paragraph("Paired seed analysis", styles["h2"]),
        paragraph(
            f"IDU-only minus Random by seed was +1.8, -2.4, +3.5, +5.5, and -1.2 percentage points. "
            f"The exact sign-flip p-value was {paired['exact_sign_flip_p_value']:.4f}. With only five seeds, "
            "the experiment has low statistical power; the correct conclusion is an observed mean advantage "
            "with meaningful seed sensitivity.",
            styles["body"],
        ),
        paragraph("Answers to Q1-Q4", styles["h2"]),
        paragraph("Q1: No. The best selected-data method remains 5.94 percentage points below Full Data.", styles["bullet"]),
        paragraph("Q2: Partly. Observed-loss IDU has the highest selected-data mean; dynamic gradient selection is only 0.30 percentage points above Random and is not reliably superior.", styles["bullet"]),
        paragraph("Q3: Yes as a trade-off, not as dominance. Dynamic gradient selection is substantially faster than Full Data, but the accuracy gap remains large and its small timing difference from Random should not be overinterpreted.", styles["bullet"]),
        paragraph("Q4: Partly. Observed-loss IDU beats the fixed static control, so iterative utility updates can help. However, gradient IDU + EXP3 is only +0.30 pp versus Random and +0.92 pp versus the balanced control, with both paired 95% intervals crossing zero. It changes selection, but does not yield a stable gain.", styles["bullet"]),
        PageBreak(),
        paragraph("5. Difficulty and SQL-component analysis", styles["h1"]),
    ])
    add_figure(story, "difficulty_breakdown.png", "Figure 3. Mean official exact match by Spider difficulty.", 150, styles)

    diff_rows = [["Method", "Easy", "Medium", "Hard", "Extra", "All"]]
    for name in ("Full Data", "Random", "Five-round IDU-only"):
        means = difficulty[name]["mean"]
        diff_rows.append([name] + [pct(means[key]) for key in ("easy", "medium", "hard", "extra", "all")])
    story.extend([
        table(diff_rows, [50 * mm, 23 * mm, 24 * mm, 23 * mm, 23 * mm, 23 * mm], font_size=7.4),
        paragraph(
            "IDU-only improves on Random for Easy (+2.70 pp), Medium (+1.98 pp), and Hard (+0.58 pp), but "
            "does not solve any Extra examples across the five runs. The benefit is therefore concentrated in "
            "less structurally demanding queries.",
            styles["body"],
        ),
    ])
    add_figure(story, "component_f1_difference.png", "Figure 4. IDU-only minus Random in official partial-match F1; sparse IUEN is excluded from the plot.", 148, styles)
    story.extend([
        paragraph(
            "The largest stable positive differences are SELECT without aggregation (+3.68 pp), SELECT "
            "(+3.62 pp), and WHERE without operator (+3.20 pp). GROUP is slightly lower (-0.66 pp). The "
            "official IUEN component is sparse and unstable when a run produces no matching set operation, "
            "so its large numerical difference is not interpreted independently.",
            styles["body"],
        ),
        paragraph("6. What the ablations show", styles["h1"]),
    ])

    idu_mean = methods["Five-round IDU-only"]["official_spider_exact_match"]["mean"]
    ablation_rows = [["Comparison", "Mean difference", "Interpretation"]]
    ablation_specs = [
        ("IDU-only vs Static", idu_mean - methods["Static Uncertainty"]["official_spider_exact_match"]["mean"], "Online utility updating adds value."),
        ("IDU-only vs Full Adaptation", idu_mean - methods["Five-round Full Adaptation"]["official_spider_exact_match"]["mean"], "All allocation components together do not help."),
        ("IDU-only vs Cluster-MAB", idu_mean - methods["Cluster-MAB Component"]["official_spider_exact_match"]["mean"], "Current clustering and bandit allocation are too coarse or unstable."),
        ("IDU-only vs Database quota", idu_mean - methods["Database-quota Component"]["official_spider_exact_match"]["mean"], "Proportional quotas reduce useful flexibility."),
    ]
    for label, delta, interpretation in ablation_specs:
        ablation_rows.append([label, pp(delta), interpretation])
    story.extend([
        table(ablation_rows, [51 * mm, 30 * mm, 88 * mm], font_size=7.5),
        paragraph(
            "The central positive result is not that the complete LEAD-style adaptation wins. Instead, the "
            "simplest iterative component - updating sample utility from model feedback - is the strongest "
            "variant. Adding cluster scheduling or database quotas increases cost without improving the mean.",
            styles["callout"],
        ),
        paragraph("Selection behaviour", styles["h2"]),
        paragraph(
            f"IDU-only and Random have a mean selected-set Jaccard overlap of {selection['mean_selection_jaccard_vs_random']:.3f}. "
            f"IDU-only covers {selection['mean_selected_databases']['Five-round IDU-only']:.1f} databases on average, "
            f"versus {selection['mean_selected_databases']['Random']:.1f} for Random. Its observed advantage "
            "does not come from maximising database count; it comes from selecting a different, dynamically "
            "updated subset.",
            styles["body"],
        ),
        paragraph("7. Gradient-based LEAD validation", styles["h1"]),
    ])

    gradient_rows = [["Comparison", "Mean difference", "95% paired interval", "Wins"]]
    for label, key in (
        ("Dynamic vs Balanced", "balanced_replay_control"),
        ("Dynamic vs Random", "random"),
        ("Dynamic vs Observed IDU", "observed_loss_idu"),
        ("Dynamic vs Full Data", "full_data"),
    ):
        item = dynamic_paired[key]
        gradient_rows.append([
            label,
            pp(item["mean_difference"]),
            f"[{pp(item['ci95'][0])}, {pp(item['ci95'][1])}]",
            f"{item['wins']}/5",
        ])
    story.extend([
        table(gradient_rows, [51 * mm, 32 * mm, 57 * mm, 25 * mm], font_size=7.4),
        paragraph(
            "Cumulative replay is the clearest successful design change. For seed 42, the gradient method rose "
            "from 10.3% without replay to 19.5% with replay. This single-seed contrast motivated the multi-seed "
            "validation; it should not be treated as an average effect.",
            styles["callout"],
        ),
        paragraph(
            "Across five seeds, dynamic gradient + EXP3 obtained 15.94% +/- 2.32 pp. Its mean was 0.92 points "
            "above the matched balanced control and 0.30 points above Random, but both paired intervals crossed "
            "zero. It was 1.14 points below observed-loss IDU. The correct interpretation is competitive but "
            "unstable performance, not reliable superiority.",
            styles["body"],
        ),
        paragraph(
            f"Dynamic selections had mean pairwise Jaccard overlap {dynamic_analysis['selection_behaviour']['dynamic_mean_pairwise_jaccard']:.2f}, "
            f"compared with {dynamic_analysis['selection_behaviour']['balanced_mean_pairwise_jaccard']:.2f} for the fixed schedule. "
            "EXP3 therefore changed the selected path, but five allocation decisions were insufficient to learn "
            "a consistently better policy. Rewards also increased mainly with training round, suggesting that "
            "round progress and difficulty-arm value were not cleanly separated.",
            styles["body"],
        ),
        paragraph("8. Manually verified qualitative cases", styles["h1"]),
        paragraph("IDU-only advantage: grouping and HAVING", styles["h2"]),
        paragraph(
            "For 'List all document ids with at least two paragraphs', IDU-only generated the correct "
            "Paragraphs + GROUP BY + HAVING structure in four of five seeds. Random failed in all five seeds, "
            "often using the Documents table or replacing HAVING with ORDER BY and LIMIT.",
            styles["body"],
        ),
        paragraph("IDU-only advantage: schema linking and comparison", styles["h2"]),
        paragraph(
            "For countries becoming independent after 1950, IDU-only produced the direct country/IndepYear > "
            "1950 query in four seeds. Random frequently selected the city table, equality, or the wrong column.",
            styles["body"],
        ),
        paragraph("Random advantage: negation", styles["h2"]),
        paragraph(
            "For nationality not equal to Russia, Random preserved the inequality in four seeds. IDU-only "
            "failed in all seeds by reversing the condition or generating unnecessary nested NOT IN queries.",
            styles["body"],
        ),
        paragraph("Random advantage: literal preservation", styles["h2"]),
        paragraph(
            "For the episode literal 'A Love of a Lifetime', Random preserved the full literal in four seeds. "
            "IDU-only repeatedly shortened the literal or selected an invalid output column.",
            styles["body"],
        ),
        paragraph(
            "Formatting-only mismatches, such as quotation style or identifier capitalisation, were excluded "
            "from the substantive case analysis. These examples explain behaviour but do not replace the "
            "official aggregate metric.",
            styles["small"],
        ),
        paragraph("9. Limitations", styles["h1"]),
        paragraph("- Five seeds expose instability but are insufficient for a strong statistical superiority claim.", styles["bullet"]),
        paragraph("- CodeT5-small has limited capacity and all methods remain weak on Extra queries.", styles["bullet"]),
        paragraph("- The gradient proxy tracks only the final decoder block of fully fine-tuned CodeT5-small rather than LoRA final-layer geometry used by the original implementation.", styles["bullet"]),
        paragraph("- Difficulty groups use pretrained-loss quantiles rather than LEAD's IFD and semantic K-means pipeline.", styles["bullet"]),
        paragraph("- EXP3 receives only five decisions, which limits policy learning and makes its reward sensitive to training-round effects.", styles["bullet"]),
        paragraph("- End-to-end timing is measured on one Apple MPS environment and should not be treated as hardware-independent throughput.", styles["bullet"]),
        paragraph("- Exact match is strict and does not directly measure execution equivalence; auxiliary normalized-string diagnostics are more formatting-sensitive.", styles["bullet"]),
        paragraph("10. Conclusion", styles["h1"]),
        paragraph(
            "Under a fixed 500-example budget, observed-loss IDU produced the best selected-data mean at 17.08%, "
            "while the more paper-aligned training-time gradient adaptation achieved 15.94%, close to Random at "
            "15.64%. The experiment supports iterative utility updating and cumulative replay as useful design "
            "elements, but it does not show a stable accuracy benefit from the present gradient proxy or EXP3 "
            "allocation. Full Data remains clearly stronger at 23.02%.",
            styles["body"],
        ),
        paragraph(
            "The most defensible outcome is a controlled positive-and-negative finding: cumulative replay prevents "
            "severe forgetting and dynamic selection changes the chosen data, while the current EXP3 reward and "
            "coarse difficulty clusters do not yield a reliable generalisation gain. This directly identifies when "
            "the LEAD adaptation helps and where its assumptions become weak in small-scale Text-to-SQL.",
            styles["callout"],
        ),
        paragraph("11. Justified next work", styles["h1"]),
        paragraph("1. Redesign the EXP3 reward to separate difficulty-arm value from the general effect of later training rounds, then test it against the same balanced control.", styles["bullet"]),
        paragraph("2. Increase allocation frequency or the number of rounds without changing the total unique-data and optimizer-step budgets, giving the bandit more feedback decisions.", styles["bullet"]),
        paragraph("3. Replace loss-quantile clusters with Text-to-SQL-aware groups based on schema and SQL structure; use additional seeds or a larger model only after this targeted design test.", styles["bullet"]),
        paragraph("References", styles["h1"]),
        paragraph("[1] T. Yu et al. Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task. EMNLP, 2018.", styles["small"]),
        paragraph("[2] Y. Wang et al. CodeT5: Identifier-aware Unified Pre-trained Encoder-Decoder Models for Code Understanding and Generation. EMNLP, 2021.", styles["small"]),
        paragraph("[3] X. Lin et al. LEAD: Iterative Data Selection for Efficient LLM Instruction Tuning. PVLDB 19(3):426-439, 2025. doi:10.14778/3778092.3778103.", styles["small"]),
    ])
    return story


def main() -> None:
    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    dynamic_metrics = json.loads(DYNAMIC_METRICS.read_text(encoding="utf-8"))
    dynamic_analysis = json.loads(DYNAMIC_ANALYSIS.read_text(encoding="utf-8"))
    styles = make_styles()
    doc = ReportDoc(str(OUTPUT), styles)
    doc.build(build_story(data, dynamic_metrics, dynamic_analysis, styles))
    print(OUTPUT)


if __name__ == "__main__":
    main()
