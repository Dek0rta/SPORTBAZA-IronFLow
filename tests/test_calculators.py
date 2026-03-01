"""
Unit tests — Sports science formula engine (formula_service.py).

Reference values were computed against the official formula specifications
and verified by running the implementation against known inputs.

All four formulas are covered:
  - Wilks 2020  (IPF polynomial)
  - DOTS        (age-independent polynomial)
  - Glossbrenner (piecewise power-law)
  - IPF GL      (IPF Goodlift — 100 × total / (A − B·exp(−C·BW)))
"""
from __future__ import annotations

import pytest

from bot.services.formula_service import (
    calculate_formula,
    dots,
    glossbrenner,
    ipf_gl,
    wilks,
    world_percentile,
)


# ─────────────────────────── Wilks 2020 ──────────────────────────────────────

@pytest.mark.parametrize("bw,gender,total,expected", [
    (82.5,  "M", 600.0, 401.94),   # male open reference
    (63.0,  "F", 350.0, 375.89),   # female open reference
    (82.5,  "M",   0.0,   0.0),    # bomb-out → 0 (calculate_formula guard)
    (40.0,  "M", 200.0, 267.08),   # lower BW bound clamp
    (200.9, "M", 900.0, 478.38),   # upper BW bound clamp
])
def test_wilks(bw: float, gender: str, total: float, expected) -> None:
    result = wilks(bw, gender, total)
    if isinstance(expected, float) and expected == 0.0:
        assert result == 0.0
    else:
        assert result == pytest.approx(expected, rel=1e-3)


# ─────────────────────────── DOTS ────────────────────────────────────────────

@pytest.mark.parametrize("bw,gender,total,expected", [
    (82.5, "M", 600.0, 406.44),   # male open reference
    (63.0, "F", 350.0, 375.53),   # female open reference
])
def test_dots(bw: float, gender: str, total: float, expected: float) -> None:
    assert dots(bw, gender, total) == pytest.approx(expected, rel=1e-3)


# ─────────────────────────── Glossbrenner ────────────────────────────────────

@pytest.mark.parametrize("bw,gender,total,expected", [
    (82.5,  "M", 600.0, 191.19),   # male ≤153.05 kg branch
    (63.0,  "F", 350.0, 127.58),   # female ≤106.50 kg branch
    (160.0, "M", 950.0, 239.55),   # male >153.05 branch
    (110.0, "F", 500.0, 179.25),   # female >106.50 branch
])
def test_glossbrenner(bw: float, gender: str, total: float, expected) -> None:
    result = glossbrenner(bw, gender, total)
    assert result == pytest.approx(expected, rel=1e-2)


# ─────────────────────────── IPF GL ──────────────────────────────────────────

@pytest.mark.parametrize("bw,gender,total,event,expected", [
    (82.5, "M", 600.0, "SBD",  83.31),   # male SBD reference
    (63.0, "F", 350.0, "SBD",  76.57),   # female SBD reference
    (82.5, "M", 250.0, "BP",  125.96),   # male BP event
    (63.0, "F", 140.0, "BP",  116.82),   # female BP event
    (82.5, "M", 600.0, "PP",   83.31),   # PP treated same as SBD
    (82.5, "M", 600.0, "DL",   83.31),   # DL treated same as SBD
    (82.5, "M",   0.0, "SBD",   0.0),    # zero total → 0
])
def test_ipf_gl(
    bw: float, gender: str, total: float, event: str, expected: float
) -> None:
    result = ipf_gl(bw, gender, total, event)
    assert result == pytest.approx(expected, rel=1e-3)


# ─────────────────────────── Score is always non-negative ────────────────────

@pytest.mark.parametrize("formula,bw,gender,total,event", [
    ("wilks",        40.0, "M",  50.0, "SBD"),
    ("dots",         40.0, "M",  50.0, "SBD"),
    ("glossbrenner", 40.0, "M",  50.0, "SBD"),
    ("ipf_gl",       40.0, "M",  50.0, "SBD"),
    ("wilks",        40.0, "F",  50.0, "SBD"),
    ("ipf_gl",       40.0, "F", 100.0, "BP"),
])
def test_score_never_negative(
    formula: str, bw: float, gender: str, total: float, event: str
) -> None:
    result = calculate_formula(formula, bw, gender, total, event)
    assert result is None or result >= 0.0


# ─────────────────────────── calculate_formula dispatcher ────────────────────

def test_calculate_formula_returns_none_for_total_formula() -> None:
    """'total' formula requires no coefficient — returns None."""
    assert calculate_formula("total", 82.5, "M", 600.0) is None


def test_calculate_formula_returns_none_for_zero_total() -> None:
    assert calculate_formula("wilks", 82.5, "M", 0.0) is None


def test_calculate_formula_returns_none_for_zero_bw() -> None:
    assert calculate_formula("dots", 0.0, "M", 600.0) is None


def test_calculate_formula_routes_correctly() -> None:
    score = calculate_formula("dots", 82.5, "M", 600.0, "SBD")
    assert score == pytest.approx(406.44, rel=1e-3)


def test_calculate_formula_ipf_gl_bp() -> None:
    score = calculate_formula("ipf_gl", 82.5, "M", 250.0, "BP")
    assert score == pytest.approx(125.96, rel=1e-3)


# ─────────────────────────── World percentile ────────────────────────────────

def test_world_percentile_median_is_50() -> None:
    """Athlete at the reference median should land near the 50th percentile."""
    pct = world_percentile("M", "-93", 575.0)  # median for M -93 = 575 kg
    assert pct is not None
    assert 45 <= pct <= 55


def test_world_percentile_above_median_over_50() -> None:
    pct = world_percentile("M", "-93", 700.0)
    assert pct is not None
    assert pct > 50


def test_world_percentile_below_median_under_50() -> None:
    pct = world_percentile("M", "-93", 400.0)
    assert pct is not None
    assert pct < 50


def test_world_percentile_unknown_category_returns_none() -> None:
    assert world_percentile("M", "-999", 500.0) is None


def test_world_percentile_clamped_to_1_99() -> None:
    pct = world_percentile("M", "-59", 1.0)  # far below any distribution
    assert pct == 1
    pct = world_percentile("M", "-59", 9999.0)  # far above
    assert pct == 99
