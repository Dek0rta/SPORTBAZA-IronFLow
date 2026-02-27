"""
Ranking engine for powerlifting competitions.

Algorithm
---------
1. Group participants by (category, gender).
2. Compute each athlete's total (sum of best lifts per discipline).
   Athletes who bombed out (no successful lift in a required discipline)
   receive total=None and are placed last.
3. Sort: total DESC; tie-break by bodyweight ASC.
4. Assign place numbers: 1, 2, 3, …  Bombed-out athletes get place=None.

This implements standard IPF ranking logic and is designed to be
extensible for Wilks / DOTS coefficient rankings in future iterations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from bot.models.models import Participant, WeightCategory, TournamentType


@dataclass
class AthleteResult:
    """A single ranked result row."""
    participant: Participant
    category:    Optional[WeightCategory]
    lift_totals: Dict[str, Optional[float]]   # {lift_type: best_weight}
    total:       Optional[float]              # None = bomb-out
    place:       Optional[int]                # None = bomb-out / no result yet

    @property
    def is_valid(self) -> bool:
        return self.total is not None


@dataclass
class CategoryRanking:
    """Ranking for a single weight/gender category."""
    category:    Optional[WeightCategory]
    gender:      str
    results:     List[AthleteResult] = field(default_factory=list)


def compute_rankings(
    participants: List[Participant],
    tournament_type: str,
) -> List[CategoryRanking]:
    """
    Compute full rankings for a tournament.

    Parameters
    ----------
    participants : loaded with .attempts and .category eager-loaded
    tournament_type : one of TournamentType.*

    Returns
    -------
    List of CategoryRanking objects sorted by category name.
    """
    lift_types: List[str] = TournamentType.LIFTS.get(tournament_type, [])

    # Group by (category_id, gender)
    groups: Dict[Tuple[Optional[int], str], List[Participant]] = {}
    for p in participants:
        key = (p.category_id, p.gender)
        groups.setdefault(key, []).append(p)

    rankings: List[CategoryRanking] = []

    for (cat_id, gender), group in groups.items():
        category = group[0].category if group else None
        results  = _rank_group(group, lift_types)
        rankings.append(CategoryRanking(category=category, gender=gender, results=results))

    # Sort categories: gender (M first), then by category upper limit
    rankings.sort(key=_category_sort_key)
    return rankings


def _rank_group(
    participants: List[Participant],
    lift_types: List[str],
) -> List[AthleteResult]:
    """
    Rank participants within one weight/gender category.

    Sorting criteria:
    - Primary:   total DESC  (higher is better)
    - Secondary: bodyweight ASC  (lighter athlete wins on tie)
    - Bomb-outs: placed at the end in original order
    """
    results: List[AthleteResult] = []

    for p in participants:
        lift_totals: Dict[str, Optional[float]] = {}
        for lt in lift_types:
            lift_totals[lt] = p.best_lift(lt)
        total = p.total(lift_types)
        results.append(
            AthleteResult(
                participant=p,
                category=p.category,
                lift_totals=lift_totals,
                total=total,
                place=None,  # assigned below
            )
        )

    # Separate valid and bombed-out
    valid    = [r for r in results if r.total is not None]
    bomb_out = [r for r in results if r.total is None]

    # Sort valid results
    valid.sort(key=lambda r: (-r.total, r.participant.bodyweight))  # type: ignore[operator]

    # Assign places (handle ties: same total + same bodyweight → same place)
    place = 1
    for i, r in enumerate(valid):
        if i > 0:
            prev = valid[i - 1]
            if not _is_tie(r, prev):
                place = i + 1
        r.place = place

    return valid + bomb_out


def _is_tie(a: AthleteResult, b: AthleteResult) -> bool:
    return a.total == b.total and a.participant.bodyweight == b.participant.bodyweight


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
        best = result.lift_totals.get(lt)
        label = labels.get(lt, lt.capitalize())
        parts.append(f"{label}: {best:g}" if best else f"{label}: —")

    breakdown = " + ".join(parts)
    if result.total is not None:
        breakdown += f" = *{result.total:g} кг*"
    return breakdown
