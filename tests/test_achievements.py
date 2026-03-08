"""
Unit tests for achievement computation logic (bot/api/achievements.py).

Uses lightweight mock objects — no database required.
"""
from __future__ import annotations

import pytest
from bot.api.achievements import compute


# ── Minimal mock objects ──────────────────────────────────────────────────────

class _Tournament:
    def __init__(self, t_type: str = "SBD", status: str = "registration"):
        self.tournament_type = t_type
        self.status          = status
        self.created_at      = None

    @property
    def lift_types(self):
        from bot.models.models import TournamentType
        return TournamentType.LIFTS.get(self.tournament_type, [])


class _Attempt:
    def __init__(self, lift_type: str, weight_kg: float, result: str = "good"):
        self.lift_type  = lift_type
        self.weight_kg  = weight_kg
        self.result     = result


class _Part:
    """Minimal Participant mock understood by compute()."""

    def __init__(
        self,
        bodyweight: float = 80.0,
        gender: str = "M",
        tournament: _Tournament | None = None,
        checked_in: bool = False,
    ):
        self.bodyweight  = bodyweight
        self.gender      = gender
        self.tournament  = tournament or _Tournament(status="registration")
        self.checked_in  = checked_in
        self.attempts: list[_Attempt] = []

    def add_attempt(self, lift_type: str, weight_kg: float, result: str = "good"):
        self.attempts.append(_Attempt(lift_type, weight_kg, result))

    def best_lift(self, lift_type: str):
        goods = [
            a.weight_kg for a in self.attempts
            if a.lift_type == lift_type and a.result == "good"
        ]
        return max(goods) if goods else None

    def total(self, lift_types: list[str]):
        total = 0.0
        for lt in lift_types:
            lifts = [a for a in self.attempts if a.lift_type == lt]
            if not lifts:
                continue
            best = self.best_lift(lt)
            if best is None:
                return None
            total += best
        return total


def _unlocked(achievements: list[dict]) -> set[str]:
    return {a["id"] for a in achievements if a["unlocked"]}


# ── first_reg ─────────────────────────────────────────────────────────────────

class TestFirstReg:
    def test_no_registrations_no_achievement(self):
        result = compute([], [], 0)
        assert "first_reg" not in _unlocked(result)

    def test_registration_in_open_tournament_unlocks_first_reg(self):
        """Bug regression: first_reg must fire even when tournament is not FINISHED."""
        part = _Part(tournament=_Tournament(status="registration"))
        result = compute([part], [], 0)
        assert "first_reg" in _unlocked(result)

    def test_registration_in_active_tournament_unlocks_first_reg(self):
        part = _Part(tournament=_Tournament(status="active"))
        result = compute([part], [], 0)
        assert "first_reg" in _unlocked(result)

    def test_registration_in_finished_tournament_unlocks_first_reg(self):
        part = _Part(tournament=_Tournament(status="finished"))
        result = compute([part], [], 0)
        assert "first_reg" in _unlocked(result)


# ── debut / veteran / experienced / legend ────────────────────────────────────

class TestCompletionAchievements:
    def _finished_part_with_lifts(self, squat=200.0, bench=150.0, dead=250.0) -> _Part:
        t = _Tournament(status="finished")
        p = _Part(tournament=t)
        p.add_attempt("squat",    squat)
        p.add_attempt("bench",    bench)
        p.add_attempt("deadlift", dead)
        return p

    def test_debut_requires_completed_tournament(self):
        # Registration only — no attempts — should NOT unlock debut
        part = _Part(tournament=_Tournament(status="registration"))
        result = compute([part], [], 0)
        assert "debut" not in _unlocked(result)

    def test_debut_unlocked_after_first_finish(self):
        p = self._finished_part_with_lifts()
        result = compute([p], [], 0)
        assert "debut" in _unlocked(result)

    def test_veteran_requires_5_completed(self):
        parts = [self._finished_part_with_lifts() for _ in range(4)]
        assert "veteran" not in _unlocked(compute(parts, [], 0))
        parts.append(self._finished_part_with_lifts())
        assert "veteran" in _unlocked(compute(parts, [], 0))

    def test_experienced_requires_10_completed(self):
        parts = [self._finished_part_with_lifts() for _ in range(10)]
        assert "experienced" in _unlocked(compute(parts, [], 0))

    def test_legend_requires_20_completed(self):
        parts = [self._finished_part_with_lifts() for _ in range(19)]
        assert "legend" not in _unlocked(compute(parts, [], 0))
        parts.append(self._finished_part_with_lifts())
        assert "legend" in _unlocked(compute(parts, [], 0))


# ── punctual (checked_in) ─────────────────────────────────────────────────────

class TestPunctual:
    def test_no_checkin_no_punctual(self):
        part = _Part(checked_in=False, tournament=_Tournament(status="registration"))
        result = compute([part], [], 0)
        assert "punctual" not in _unlocked(result)

    def test_checkin_in_active_tournament_unlocks_punctual(self):
        """Bug regression: punctual must fire for non-finished tournaments too."""
        part = _Part(checked_in=True, tournament=_Tournament(status="active"))
        result = compute([part], [], 0)
        assert "punctual" in _unlocked(result)


# ── clean_win / perfectionist ─────────────────────────────────────────────────

class TestCleanWin:
    def test_9_good_attempts_unlocks_clean_win(self):
        t = _Tournament("SBD", "finished")
        p = _Part(tournament=t)
        for lift in ["squat", "bench", "deadlift"]:
            for _ in range(3):
                p.add_attempt(lift, 100.0, "good")
        result = compute([p], [], 0)
        assert "clean_win" in _unlocked(result)

    def test_less_than_9_good_does_not_unlock(self):
        t = _Tournament("SBD", "finished")
        p = _Part(tournament=t)
        p.add_attempt("squat", 100.0, "good")
        p.add_attempt("bench", 100.0, "bad")
        result = compute([p], [], 0)
        assert "clean_win" not in _unlocked(result)

    def test_perfectionist_requires_3_clean_tournaments(self):
        def clean_part():
            t = _Tournament("SBD", "finished")
            p = _Part(tournament=t)
            for lift in ["squat", "bench", "deadlift"]:
                for _ in range(3):
                    p.add_attempt(lift, 100.0, "good")
            return p

        parts = [clean_part(), clean_part()]
        assert "perfectionist" not in _unlocked(compute(parts, [], 0))
        parts.append(clean_part())
        assert "perfectionist" in _unlocked(compute(parts, [], 0))


# ── weight milestones ─────────────────────────────────────────────────────────

class TestWeightMilestones:
    def _sbd_part(self, squat: float, bench: float, dead: float) -> _Part:
        t = _Tournament("SBD", "finished")
        p = _Part(bodyweight=90.0, gender="M", tournament=t)
        p.add_attempt("squat", squat)
        p.add_attempt("bench", bench)
        p.add_attempt("deadlift", dead)
        return p

    def test_club_500_at_exactly_500(self):
        p = self._sbd_part(200, 150, 150)  # total = 500
        assert "club_500" in _unlocked(compute([p], [], 0))

    def test_below_500_no_club(self):
        p = self._sbd_part(150, 100, 100)  # total = 350
        assert "club_500" not in _unlocked(compute([p], [], 0))

    def test_club_650_and_titan(self):
        p650 = self._sbd_part(250, 170, 230)   # 650
        assert "club_650" in _unlocked(compute([p650], [], 0))
        assert "titan" not in _unlocked(compute([p650], [], 0))

        p800 = self._sbd_part(300, 210, 290)   # 800
        assert "titan" in _unlocked(compute([p800], [], 0))


# ── all definitions present in output ────────────────────────────────────────

def test_all_definitions_returned():
    result = compute([], [], 0)
    from bot.api.achievements import DEFINITIONS
    ids_in_result = {a["id"] for a in result}
    ids_defined   = {d["id"] for d in DEFINITIONS}
    assert ids_in_result == ids_defined


def test_no_extra_unlocked_for_empty_input():
    result = compute([], [], 0)
    assert _unlocked(result) == set()
