"""
Ranking engine for powerlifting competitions — Iron Flow v2.

Algorithm (per weight/gender category)
----------------------------------------
1. Group participants by (category, gender).
2. Compute each athlete's total (sum of best lifts per discipline).
   Athletes who bombed out (no successful lift in a required discipline)
   receive total=None and are placed last.
3. Apply the tournament's scoring formula (Wilks / DOTS / Glossbrenner / IPF GL).
4. Sort: formula_score DESC (or total DESC when formula=total);
   tie-break by bodyweight ASC.
5. Assign place numbers: 1, 2, 3 …  Bomb-outs get place=None.

Overall (absolute) rankings
-----------------------------
Cross all weight categories: rank all valid athletes by formula_score DESC.
This produces the "Overall Champion" result.

Division rankings
-----------------
Group by age_category first, then by weight/gender category inside each division.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from bot.models.models import (
    Participant, WeightCategory, TournamentType, FormulaType, AgeCategory
)
from bot.services.formula_service import calculate_formula


@dataclass
class AthleteResult:
    """A single ranked result row."""
    participant:   Participant
    category:      Optional[WeightCategory]
    lift_totals:   Dict[str, Optional[float]]   # {lift_type: best_weight}
    total:         Optional[float]              # None = bomb-out
    formula_score: Optional[float]             # Score by active formula (None if no formula)
    place:         Optional[int]               # None = bomb-out / no result yet

    @property
    def is_valid(self) -> bool:
        return self.total is not None

    @property
    def sort_key(self) -> float:
        """Primary sort value: formula_score if available, else total."""
        if self.formula_score is not None:
            return self.formula_score
        return self.total if self.total is not None else 0.0


@dataclass
class CategoryRanking:
    """Ranking for a single weight/gender category."""
    category: Optional[WeightCategory]
    gender:   str
    results:  List[AthleteResult] = field(default_factory=list)

    @property
    def category_display(self) -> str:
        if self.category:
            return self.category.display_name
        gender_str = "М" if self.gender == "M" else "Ж"
        return f"Без категории {gender_str}"


@dataclass
class DivisionRanking:
    """Ranking for one age division (contains sub-divisions by weight)."""
    age_category:     str
    age_label:        str
    sub_rankings:     List[CategoryRanking] = field(default_factory=list)


# ─────────────────────────── Main entry points ────────────────────────────────

def compute_rankings(
    participants: List[Participant],
    tournament_type: str,
    scoring_formula: str = FormulaType.TOTAL,
) -> List[CategoryRanking]:
    """
    Compute full rankings for a tournament, grouped by weight/gender category.

    Parameters
    ----------
    participants     : loaded with .attempts and .category eager-loaded
    tournament_type  : one of TournamentType.*
    scoring_formula  : one of FormulaType.*

    Returns
    -------
    List of CategoryRanking sorted by gender → category weight limit.
    """
    lift_types: List[str] = TournamentType.LIFTS.get(tournament_type, [])

    groups: Dict[Tuple[Optional[int], str], List[Participant]] = {}
    for p in participants:
        key = (p.category_id, p.gender)
        groups.setdefault(key, []).append(p)

    rankings: List[CategoryRanking] = []
    for (cat_id, gender), group in groups.items():
        category = group[0].category if group else None
        results  = _rank_group(group, lift_types, scoring_formula, tournament_type)
        rankings.append(CategoryRanking(category=category, gender=gender, results=results))

    rankings.sort(key=_category_sort_key)
    return rankings


def compute_overall_rankings(
    participants: List[Participant],
    tournament_type: str,
    scoring_formula: str = FormulaType.TOTAL,
) -> List[AthleteResult]:
    """
    Compute the Absolute/Overall ranking across ALL weight categories.

    Athletes are ranked by formula_score (or total when formula=total),
    regardless of weight class. This yields the "Overall Champion".

    Returns a flat sorted list (valid athletes only, bomb-outs excluded).
    """
    lift_types = TournamentType.LIFTS.get(tournament_type, [])
    valid_results: List[AthleteResult] = []

    for p in participants:
        total = p.total(lift_types)
        if total is None:
            continue  # bomb-out excluded from overall

        lift_totals = {lt: p.best_lift(lt) for lt in lift_types}
        formula_score = calculate_formula(
            scoring_formula, p.bodyweight, p.gender, total, tournament_type
        )
        valid_results.append(
            AthleteResult(
                participant=p,
                category=p.category,
                lift_totals=lift_totals,
                total=total,
                formula_score=formula_score,
                place=None,
            )
        )

    valid_results.sort(key=lambda r: (-r.sort_key, r.participant.bodyweight))

    place = 1
    for i, r in enumerate(valid_results):
        if i > 0 and _is_tie(r, valid_results[i - 1]):
            r.place = valid_results[i - 1].place
        else:
            r.place = place
        place = i + 2

    return valid_results


def compute_division_rankings(
    participants: List[Participant],
    tournament_type: str,
    scoring_formula: str = FormulaType.TOTAL,
) -> List[DivisionRanking]:
    """
    Compute rankings grouped by age division → weight sub-division.

    Returns a list of DivisionRanking (one per age category present),
    each containing CategoryRanking sub-divisions.
    """
    lift_types = TournamentType.LIFTS.get(tournament_type, [])

    # Group by age_category
    age_groups: Dict[str, List[Participant]] = {}
    for p in participants:
        age_cat = p.age_category or AgeCategory.OPEN
        age_groups.setdefault(age_cat, []).append(p)

    divisions: List[DivisionRanking] = []
    age_order = list(AgeCategory.LABELS.keys())

    for age_cat in age_order:
        if age_cat not in age_groups:
            continue
        group = age_groups[age_cat]
        sub_rankings = compute_rankings(group, tournament_type, scoring_formula)
        divisions.append(
            DivisionRanking(
                age_category=age_cat,
                age_label=AgeCategory.LABELS.get(age_cat, age_cat),
                sub_rankings=sub_rankings,
            )
        )

    return divisions


# ─────────────────────────── Internal helpers ─────────────────────────────────

def _rank_group(
    participants: List[Participant],
    lift_types: List[str],
    scoring_formula: str,
    tournament_type: str,
) -> List[AthleteResult]:
    results: List[AthleteResult] = []

    for p in participants:
        lift_totals = {lt: p.best_lift(lt) for lt in lift_types}
        total       = p.total(lift_types)
        formula_score = None
        if total is not None:
            formula_score = calculate_formula(
                scoring_formula, p.bodyweight, p.gender, total, tournament_type
            )
        results.append(
            AthleteResult(
                participant=p,
                category=p.category,
                lift_totals=lift_totals,
                total=total,
                formula_score=formula_score,
                place=None,
            )
        )

    valid    = [r for r in results if r.total is not None]
    bomb_out = [r for r in results if r.total is None]

    valid.sort(key=lambda r: (-r.sort_key, r.participant.bodyweight))

    place = 1
    for i, r in enumerate(valid):
        if i > 0 and _is_tie(r, valid[i - 1]):
            r.place = valid[i - 1].place
        else:
            r.place = place
        place = i + 2

    return valid + bomb_out


def _is_tie(a: AthleteResult, b: AthleteResult) -> bool:
    """Two athletes tie if both their sort key and bodyweight are identical."""
    return abs(a.sort_key - b.sort_key) < 0.01 and a.participant.bodyweight == b.participant.bodyweight


def _category_sort_key(ranking: CategoryRanking) -> tuple:
    gender_order = {"M": 0, "F": 1}
    gender_val   = gender_order.get(ranking.gender, 2)

    if ranking.category is None:
        return (gender_val, float("inf"), "")

    name = ranking.category.name
    if name.endswith("+"):
        limit = float(name[:-1])
        return (gender_val, limit + 0.1, name)
    else:
        limit = float(name.lstrip("-"))
        return (gender_val, limit, name)


# ─────────────────────────── Formatting helpers ───────────────────────────────

def format_total_breakdown(
    result: AthleteResult,
    lift_types: List[str],
) -> str:
    """
    Human-readable total breakdown for notifications.
    Example: "Приседания: 200 + Жим: 175 + Тяга: 230 = 605 кг"
    """
    labels = TournamentType.LIFT_LABELS
    parts = []
    for lt in lift_types:
        best  = result.lift_totals.get(lt)
        label = labels.get(lt, lt.capitalize())
        parts.append(f"{label}: {best:g}" if best else f"{label}: —")

    breakdown = " + ".join(parts)
    if result.total is not None:
        breakdown += f" = *{result.total:g} кг*"
    return breakdown


def format_result_with_formula(
    result: AthleteResult,
    formula: str,
) -> str:
    """
    Format athlete name + total + formula score for results display.
    Example: "Иванов Иван — 605 кг [DOTS: 412.5]"
    """
    name = result.participant.full_name
    if result.total is None:
        return f"{name} — бомб-аут"

    total_str = f"{result.total:g} кг"
    if result.formula_score is not None and formula != FormulaType.TOTAL:
        label = FormulaType.SHORT.get(formula, formula.upper())
        return f"{name} — {total_str} [{label}: {result.formula_score:.2f}]"
    return f"{name} — {total_str}"
