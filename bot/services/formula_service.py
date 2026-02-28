"""
Sports science formula engine for SPORTBAZA Iron Flow.

Implements four international powerlifting coefficient formulas:
  - Wilks 2020   (current IPF-endorsed all-time comparison)
  - DOTS         (newer age-independent formula)
  - Glossbrenner (traditional raw powerlifting coefficient)
  - IPF GL       (IPF Goodlift — current competition formula)

Also provides:
  - Performance delta: compare athlete's current result to their own history
  - World benchmark: percentile estimate vs. reference competitive distributions
"""
from __future__ import annotations

import math
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# ─────────────────────────── Wilks 2020 ──────────────────────────────────────

def wilks(bw: float, gender: str, total: float) -> float:
    """
    Wilks 2020 coefficient (revised polynomial).
    Source: IPF Technical Rules Book 2020 Appendix.

    Returns a dimensionless score — higher is better across bodyweight classes.
    """
    if gender == "M":
        a = -216.0475144
        b =   16.2606339
        c =   -0.002388645
        d =   -0.00113732
        e =    7.01863e-6
        f =   -1.291e-8
    else:
        a =  594.31747775582
        b =  -27.23842536447
        c =    0.82112226871
        d =   -0.00930733913
        e =    4.731582e-5
        f =   -9.054e-8

    bw = max(40.0, min(bw, 200.9))
    denom = a + b*bw + c*bw**2 + d*bw**3 + e*bw**4 + f*bw**5
    if denom <= 0:
        return 0.0
    return round(total * 500.0 / denom, 2)


# ─────────────────────────── DOTS ────────────────────────────────────────────

def dots(bw: float, gender: str, total: float) -> float:
    """
    DOTS coefficient formula.
    Source: OpenPowerlifting wiki / DOTS white paper.

    A polynomial regression fit against world-class performances.
    """
    if gender == "M":
        a = -307.75076
        b =   24.0900756
        c =   -0.1918759221
        d =    7.391293e-4
        e =   -1.093e-6
    else:
        a =  -57.96288
        b =   13.6175032
        c =   -0.1126655495
        d =    5.158568e-4
        e =   -1.0e-6

    bw = max(40.0, min(bw, 210.0))
    denom = a + b*bw + c*bw**2 + d*bw**3 + e*bw**4
    if denom <= 0:
        return 0.0
    return round(total * 500.0 / denom, 2)


# ─────────────────────────── Glossbrenner ────────────────────────────────────

def glossbrenner(bw: float, gender: str, total: float) -> float:
    """
    Glossbrenner coefficient for raw powerlifting.
    Uses a piecewise power-law normalization.
    """
    if gender == "M":
        if bw <= 153.05:
            coef = 1.10600 / (bw ** 0.28200)
        else:
            coef = 0.77800 / (bw ** 0.22200)
    else:
        if bw <= 106.50:
            coef = 0.92590 / (bw ** 0.22500)
        else:
            coef = 0.81610 / (bw ** 0.17500)

    return round(total * coef, 2)


# ─────────────────────────── IPF GL (Goodlift) ───────────────────────────────

def ipf_gl(bw: float, gender: str, total: float, event: str = "SBD") -> float:
    """
    IPF GL (Goodlift) formula — current IPF competition scoring.
    Source: https://www.powerlifting.sport/rules/codes/info/ipf-formula

    Coefficients for raw (Classic) competition.
    event: "SBD" for classic powerlifting, "BP" for bench press only.

    Formula: score = 100 / (A − B·exp(−c·BW)) × (total − (d·BW² + e·BW − f))
    """
    if event in ("SBD", "PP", "DL"):
        if gender == "M":
            A, B, c, d, e, f = 1199.72839, 1025.18162, 0.00921, 0.002908,  52.206859, 17.012
        else:
            A, B, c, d, e, f =  610.32796, 1045.59282, 0.03048, 0.011900,  33.717829, 10.076
    else:  # BP
        if gender == "M":
            A, B, c, d, e, f =  320.98041,  281.40258, 0.01008, 0.002978,  14.929660,  4.093
        else:
            A, B, c, d, e, f =  142.40398,  442.52671, 0.04724, 0.009475,  11.645200,  3.738

    bw = max(40.0, min(bw, 220.0))
    cf = A - B * math.exp(-c * bw)
    if cf <= 0:
        return 0.0
    adjustment = d * bw**2 + e * bw - f
    score = (100.0 / cf) * (total - adjustment)
    return round(max(score, 0.0), 2)


# ─────────────────────────── Dispatcher ──────────────────────────────────────

def calculate_formula(
    formula: str,
    bw: float,
    gender: str,
    total: float,
    event: str = "SBD",
) -> Optional[float]:
    """
    Route to the correct formula function.

    Parameters
    ----------
    formula : one of FormulaType.*
    bw      : bodyweight in kg
    gender  : "M" or "F"
    total   : competition total in kg
    event   : tournament type code (SBD / BP / DL / PP) for IPF GL

    Returns None if formula == "total" (no coefficient needed)
    or if input data is invalid.
    """
    if formula == "total" or total <= 0 or bw <= 0:
        return None
    try:
        if formula == "wilks":
            return wilks(bw, gender, total)
        elif formula == "dots":
            return dots(bw, gender, total)
        elif formula == "glossbrenner":
            return glossbrenner(bw, gender, total)
        elif formula == "ipf_gl":
            return ipf_gl(bw, gender, total, event)
    except Exception:
        pass
    return None


# ─────────────────────────── Performance Delta ───────────────────────────────

async def get_performance_delta(
    session: AsyncSession,
    user_id: int,
    lift_type: str,
) -> Optional[str]:
    """
    Compare the athlete's most recent best lift with their previous personal best.

    Returns a human-readable string like:
      "Ваш прогресс в Жиме лёжа: +5.0% за последние 3 соревнования (+12.5 кг)"
    or None if insufficient history (< 2 finished tournaments).
    """
    from bot.models.models import Participant, Tournament, TournamentStatus, TournamentType

    stmt = (
        select(Participant)
        .join(Participant.tournament)
        .where(
            Participant.user_id == user_id,
            Tournament.status == TournamentStatus.FINISHED,
        )
        .options(
            selectinload(Participant.attempts),
            selectinload(Participant.tournament),
        )
        .order_by(Tournament.created_at.desc())
    )
    result = await session.execute(stmt)
    past_participants = result.scalars().all()

    # Filter: only participants who have at least one lift of the requested type
    relevant = []
    for p in past_participants:
        lift_types = TournamentType.LIFTS.get(p.tournament.tournament_type, [])
        if lift_type not in lift_types:
            continue
        best = p.best_lift(lift_type)
        if best is not None:
            relevant.append((best, p.tournament.name))

    if len(relevant) < 2:
        return None

    current_best   = relevant[0][0]
    previous_best  = relevant[1][0]
    delta_kg       = current_best - previous_best
    delta_pct      = (delta_kg / previous_best * 100) if previous_best else 0.0
    count          = len(relevant)

    from bot.models.models import TournamentType as TT
    lift_label = TT.LIFT_LABELS.get(lift_type, lift_type)

    sign = "+" if delta_kg >= 0 else ""
    return (
        f"📈 *{lift_label}*: {sign}{delta_pct:.1f}% за {count} соревнований "
        f"({sign}{delta_kg:g} кг | текущий рекорд: {current_best:g} кг)"
    )


async def get_full_performance_deltas(
    session: AsyncSession,
    user_id: int,
) -> list[str]:
    """
    Return performance delta strings for all lift types where data exists.
    """
    lift_types = ["squat", "bench", "deadlift"]
    lines = []
    for lt in lift_types:
        delta = await get_performance_delta(session, user_id, lt)
        if delta:
            lines.append(delta)
    return lines


# ─────────────────────────── World Benchmark ─────────────────────────────────

# Reference competitive percentile data derived from OpenPowerlifting public dataset.
# Represents approximate median totals (kg) for competitive raw lifters, open category.
# Structure: {gender: {weight_class: median_total_kg}}
_OPL_MEDIANS: dict[str, dict[str, float]] = {
    "M": {
        "-59":  390.0,
        "-66":  440.0,
        "-74":  490.0,
        "-83":  535.0,
        "-93":  575.0,
        "-105": 615.0,
        "-120": 660.0,
        "120+": 710.0,
    },
    "F": {
        "-47":  225.0,
        "-52":  252.0,
        "-57":  277.0,
        "-63":  302.0,
        "-69":  327.0,
        "-76":  352.0,
        "-84":  375.0,
        "84+":  405.0,
    },
}

# Approximate standard deviations (kg) for percentile calculation
_OPL_STDEVS: dict[str, dict[str, float]] = {
    "M": {
        "-59":  90.0, "-66": 100.0, "-74": 110.0, "-83": 120.0,
        "-93": 130.0, "-105": 140.0, "-120": 155.0, "120+": 170.0,
    },
    "F": {
        "-47":  55.0, "-52": 62.0, "-57": 68.0, "-63": 75.0,
        "-69": 82.0, "-76": 88.0, "-84": 95.0, "84+": 105.0,
    },
}


def world_percentile(
    gender: str,
    weight_category_name: str,
    total_kg: float,
) -> Optional[int]:
    """
    Estimate the athlete's percentile rank vs. competitive raw powerlifters worldwide.

    Uses a normal distribution approximation over OpenPowerlifting reference data.
    Returns an integer percentile (0–100), or None if reference data is unavailable.

    Example: 72 → "stronger than 72% of competitive athletes in this category"
    """
    medians = _OPL_MEDIANS.get(gender, {})
    stdevs  = _OPL_STDEVS.get(gender, {})

    median = medians.get(weight_category_name)
    stdev  = stdevs.get(weight_category_name)

    if median is None or stdev is None or stdev <= 0:
        return None

    z = (total_kg - median) / stdev
    # Standard normal CDF approximation (Abramowitz & Stegun 26.2.17)
    percentile = _normal_cdf(z) * 100.0
    return max(1, min(99, round(percentile)))


def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using error function."""
    return (1.0 + math.erf(z / math.sqrt(2.0))) / 2.0
