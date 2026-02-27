"""
Academic Impact Report generator.

Produces anonymized competition analytics designed for portfolio presentation
targeting Data Engineering / Data Science roles in the US market.

Metrics computed
----------------
- Participant demographics (gender split, weight distribution)
- Attempt Accuracy % per discipline (successful / total judged)
- Total tonnage lifted across the competition
- Average total by weight category
- Performance spread (min / max / median total)

All comments below are intentionally written in English to showcase
data-engineering competency.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bot.models.models import Participant, AttemptResult, TournamentType
from bot.services.ranking_service import compute_rankings


@dataclass
class LiftAccuracy:
    """Accuracy metrics for a single lift discipline."""
    lift_type:    str
    total_judged: int = 0
    successful:   int = 0

    @property
    def accuracy_pct(self) -> float:
        if self.total_judged == 0:
            return 0.0
        return round(self.successful / self.total_judged * 100, 1)


@dataclass
class AnalyticsReport:
    """Aggregated competition analytics payload."""
    tournament_name: str
    tournament_type: str

    # Demographics
    total_participants: int           = 0
    male_count:         int           = 0
    female_count:       int           = 0

    # Attempt accuracy per discipline
    accuracy_by_lift:   Dict[str, LiftAccuracy] = field(default_factory=dict)

    # Tonnage
    total_tonnage_kg:   float = 0.0

    # Totals distribution
    valid_totals:       List[float]   = field(default_factory=list)

    # Category breakdown: category_name → avg_total
    avg_total_by_cat:   Dict[str, Optional[float]] = field(default_factory=dict)

    # ── Derived statistics ────────────────────────────────────────────────────

    @property
    def median_total(self) -> Optional[float]:
        return round(statistics.median(self.valid_totals), 2) if self.valid_totals else None

    @property
    def max_total(self) -> Optional[float]:
        return max(self.valid_totals) if self.valid_totals else None

    @property
    def min_total(self) -> Optional[float]:
        return min(self.valid_totals) if self.valid_totals else None


def build_analytics_report(
    tournament_name: str,
    tournament_type: str,
    participants: List[Participant],
) -> AnalyticsReport:
    """
    Compute competition analytics from raw participant + attempt data.

    Data pipeline:
    1. Filter active (non-withdrawn) participants.
    2. Aggregate attempt results per lift discipline.
    3. Compute Accuracy % = successful_attempts / total_judged_attempts.
    4. Sum all lifted weights for total tonnage (non-zero successful lifts).
    5. Collect valid totals for statistical summary.
    6. Build per-category average totals.
    """
    lift_types = TournamentType.LIFTS.get(tournament_type, [])

    report = AnalyticsReport(
        tournament_name=tournament_name,
        tournament_type=tournament_type,
        accuracy_by_lift={lt: LiftAccuracy(lift_type=lt) for lt in lift_types},
    )

    # Step 1: filter active participants
    active = [
        p for p in participants
        if p.status != "withdrawn"
    ]
    report.total_participants = len(active)
    report.male_count   = sum(1 for p in active if p.gender == "M")
    report.female_count = sum(1 for p in active if p.gender == "F")

    # Step 2-4: iterate attempts for accuracy + tonnage
    for p in active:
        for attempt in p.attempts:
            if attempt.result is None:
                continue   # not yet judged — skip

            lt = attempt.lift_type
            if lt not in report.accuracy_by_lift:
                continue

            acc = report.accuracy_by_lift[lt]
            acc.total_judged += 1

            if attempt.result == AttemptResult.GOOD and attempt.weight_kg:
                acc.successful      += 1
                report.total_tonnage_kg += attempt.weight_kg   # tonnage counts all good lifts

    # Step 5: collect valid totals
    rankings = compute_rankings(active, tournament_type)
    for cat_ranking in rankings:
        cat_totals = []
        for r in cat_ranking.results:
            if r.total is not None:
                report.valid_totals.append(r.total)
                cat_totals.append(r.total)

        # Step 6: per-category average
        cat_name = cat_ranking.category.display_name if cat_ranking.category else "Без категории"
        if cat_totals:
            report.avg_total_by_cat[cat_name] = round(
                sum(cat_totals) / len(cat_totals), 2
            )
        else:
            report.avg_total_by_cat[cat_name] = None

    return report


def format_report_text(report: AnalyticsReport) -> str:
    """Render the analytics report as a Markdown-formatted Telegram message."""
    lift_labels = TournamentType.LIFT_LABELS

    lines = [
        f"📊 *Academic Impact Report*",
        f"🏆 _{report.tournament_name}_ · {TournamentType.LABELS.get(report.tournament_type, '')}",
        "",
        "━━━ 👥 Демография ━━━",
        f"Всего участников: `{report.total_participants}`",
        f"👨 Мужчин: `{report.male_count}` · 👩 Женщин: `{report.female_count}`",
        "",
        "━━━ 🎯 Точность подходов ━━━",
    ]

    for lt, acc in report.accuracy_by_lift.items():
        label = lift_labels.get(lt, lt.capitalize())
        bar   = _progress_bar(acc.accuracy_pct)
        lines.append(
            f"{label}: `{acc.successful}/{acc.total_judged}` "
            f"— `{acc.accuracy_pct}%` {bar}"
        )

    lines += [
        "",
        "━━━ 💪 Тоннаж ━━━",
        f"Поднято суммарно: `{report.total_tonnage_kg:,.1f} кг`",
        "",
        "━━━ 📈 Распределение тоталлов ━━━",
    ]

    if report.valid_totals:
        lines += [
            f"Максимум:  `{report.max_total:g} кг`",
            f"Медиана:   `{report.median_total:g} кг`",
            f"Минимум:   `{report.min_total:g} кг`",
        ]
    else:
        lines.append("_Нет завершённых выступлений_")

    if report.avg_total_by_cat:
        lines += ["", "━━━ 🏅 Средний тоталл по категориям ━━━"]
        for cat_name, avg in report.avg_total_by_cat.items():
            avg_str = f"`{avg:g} кг`" if avg else "_—_"
            lines.append(f"{cat_name}: {avg_str}")

    return "\n".join(lines)


def _progress_bar(pct: float, length: int = 10) -> str:
    """ASCII progress bar: ████░░░░░░  68%"""
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)
