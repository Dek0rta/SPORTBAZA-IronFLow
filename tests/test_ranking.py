"""
Unit tests — Ranking engine (ranking_service.py).

Uses lightweight mock objects that replicate the interface expected by
ranking_service functions: best_lift(), total(), bodyweight, gender,
age_category, category, category_id.

No database is required for these tests.
"""
from __future__ import annotations

import pytest

from bot.services.ranking_service import (
    compute_overall_rankings,
    compute_rankings,
    format_result_with_formula,
)
from tests.conftest import _MockParticipant


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _sbd_participant(
    name: str,
    bw: float,
    gender: str,
    squat: float,
    bench: float,
    deadlift: float,
    age_category: str = "open",
) -> _MockParticipant:
    p = _MockParticipant(name, bw, gender, age_category)
    p.add_attempt("squat",    squat,    "good")
    p.add_attempt("bench",    bench,    "good")
    p.add_attempt("deadlift", deadlift, "good")
    return p


def _bomb_out_participant(
    name: str, bw: float, gender: str, age_category: str = "open"
) -> _MockParticipant:
    """Participant with no good squat → bomb-out."""
    p = _MockParticipant(name, bw, gender, age_category)
    p.add_attempt("squat",    200.0, "bad")
    p.add_attempt("bench",    150.0, "good")
    p.add_attempt("deadlift", 220.0, "good")
    return p


# ─────────────────────────── Total calculation ───────────────────────────────

class TestParticipantInterface:
    def test_total_sums_best_lifts(self) -> None:
        p = _sbd_participant("A", 82.5, "M", 200, 140, 230)
        assert p.total(["squat", "bench", "deadlift"]) == pytest.approx(570.0)

    def test_best_lift_picks_maximum(self) -> None:
        p = _MockParticipant("A", 82.5, "M")
        p.add_attempt("squat", 190.0, "bad")
        p.add_attempt("squat", 200.0, "good")
        p.add_attempt("squat", 205.0, "bad")
        assert p.best_lift("squat") == 200.0

    def test_bomb_out_total_is_none(self) -> None:
        p = _bomb_out_participant("A", 82.5, "M")
        assert p.total(["squat", "bench", "deadlift"]) is None

    def test_no_attempts_for_lift_skipped_in_total(self) -> None:
        """If no attempts are entered for a lift, don't penalise (in-progress)."""
        p = _MockParticipant("A", 82.5, "M")
        p.add_attempt("bench",    150.0, "good")
        p.add_attempt("deadlift", 230.0, "good")
        # No squat attempts at all
        assert p.total(["squat", "bench", "deadlift"]) == pytest.approx(380.0)


# ─────────────────────────── compute_rankings ────────────────────────────────

class TestComputeRankings:
    def test_places_assigned_in_total_order(self) -> None:
        participants = [
            _sbd_participant("Alpha", 82.5, "M", 200, 130, 220),   # 550 kg
            _sbd_participant("Beta",  83.0, "M", 180, 120, 200),   # 500 kg
            _sbd_participant("Gamma", 82.0, "M", 210, 140, 240),   # 590 kg
        ]
        rankings = compute_rankings(participants, "SBD", "total")

        # All in one category-less group
        assert len(rankings) == 1
        results = rankings[0].results
        assert results[0].participant.full_name == "Gamma"
        assert results[0].place == 1
        assert results[1].participant.full_name == "Alpha"
        assert results[1].place == 2
        assert results[2].participant.full_name == "Beta"
        assert results[2].place == 3

    def test_bomb_out_placed_last(self) -> None:
        participants = [
            _sbd_participant("Valid", 82.5, "M", 200, 130, 220),
            _bomb_out_participant("Bomb", 80.0, "M"),
        ]
        rankings = compute_rankings(participants, "SBD", "total")
        results = rankings[0].results
        # Bomb-out always last with no place
        assert results[-1].participant.full_name == "Bomb"
        assert results[-1].place is None

    def test_tiebreak_by_bodyweight_asc(self) -> None:
        """Equal totals → lighter athlete wins."""
        participants = [
            _sbd_participant("Heavy", 93.0, "M", 200, 130, 220),   # 550 kg, heavier
            _sbd_participant("Light", 90.0, "M", 200, 130, 220),   # 550 kg, lighter
        ]
        rankings = compute_rankings(participants, "SBD", "total")
        results = rankings[0].results
        assert results[0].participant.full_name == "Light"
        assert results[0].place == 1
        assert results[1].participant.full_name == "Heavy"
        assert results[1].place == 2

    def test_tie_same_weight_shares_place(self) -> None:
        """Identical total + identical BW → same place number."""
        participants = [
            _sbd_participant("A", 82.5, "M", 200, 130, 220),  # 550 kg
            _sbd_participant("B", 82.5, "M", 200, 130, 220),  # 550 kg
        ]
        rankings = compute_rankings(participants, "SBD", "total")
        results = rankings[0].results
        assert results[0].place == results[1].place == 1

    def test_formula_ranking_uses_formula_score(self) -> None:
        """With DOTS formula, lighter athlete with same total can rank higher."""
        # Both lift 600 kg total but different bodyweights → different DOTS scores
        participants = [
            _sbd_participant("Heavy", 120.0, "M", 220, 160, 220),  # 600 kg, heavy
            _sbd_participant("Light",  74.0, "M", 200, 150, 250),  # 600 kg, light
        ]
        rankings = compute_rankings(participants, "SBD", "dots")
        results = rankings[0].results
        # Lighter athlete should rank higher due to DOTS coefficient
        assert results[0].participant.full_name == "Light"


# ─────────────────────────── compute_overall_rankings ────────────────────────

class TestComputeOverallRankings:
    def test_returns_flat_sorted_list(self) -> None:
        participants = [
            _sbd_participant("A", 74.0, "M", 190, 130, 210),  # 530 kg
            _sbd_participant("B", 93.0, "M", 220, 150, 240),  # 610 kg
            _sbd_participant("C", 83.0, "M", 210, 140, 230),  # 580 kg
        ]
        overall = compute_overall_rankings(participants, "SBD", "total")
        assert len(overall) == 3
        assert overall[0].participant.full_name == "B"
        assert overall[0].place == 1

    def test_bomb_outs_excluded_from_overall(self) -> None:
        participants = [
            _sbd_participant("Valid",  82.5, "M", 200, 130, 220),
            _bomb_out_participant("Bomb",  80.0, "M"),
        ]
        overall = compute_overall_rankings(participants, "SBD", "total")
        names = [r.participant.full_name for r in overall]
        assert "Bomb" not in names

    def test_formula_score_attached(self) -> None:
        participants = [_sbd_participant("A", 82.5, "M", 200, 130, 220)]
        overall = compute_overall_rankings(participants, "SBD", "dots")
        assert overall[0].formula_score is not None
        assert overall[0].formula_score > 0


# ─────────────────────────── Formatting helpers ──────────────────────────────

class TestFormatResultWithFormula:
    def test_format_with_dots_score(self) -> None:
        p = _sbd_participant("Иванов Иван", 82.5, "M", 200, 130, 220)
        overall = compute_overall_rankings([p], "SBD", "dots")
        text = format_result_with_formula(overall[0], "dots")
        assert "Иванов Иван" in text
        assert "DOTS" in text
        assert "550" in text

    def test_format_with_total_formula_no_score_label(self) -> None:
        p = _sbd_participant("Петров Пётр", 83.0, "M", 200, 130, 220)
        overall = compute_overall_rankings([p], "SBD", "total")
        text = format_result_with_formula(overall[0], "total")
        assert "Петров Пётр" in text
        assert "DOTS" not in text  # no formula label when formula=total

    def test_format_bomb_out(self) -> None:
        p = _bomb_out_participant("Сидоров Сидор", 80.0, "M")
        from bot.services.ranking_service import AthleteResult
        result = AthleteResult(
            participant=p, category=None,
            lift_totals={}, total=None,
            formula_score=None, place=None,
        )
        text = format_result_with_formula(result, "total")
        assert "бомб-аут" in text.lower()
