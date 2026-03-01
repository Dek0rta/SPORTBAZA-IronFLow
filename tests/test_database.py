"""
Integration tests — Database CRUD via tournament_service / records_service.

Each test function receives a fresh in-memory SQLite database through the
`async_session` fixture defined in conftest.py.  No external services or
files are touched.

Coverage:
  - User upsert / lookup
  - Tournament create / read / list / formula update / delete
  - Weight-category bulk creation
  - Participant registration, duplicate guard, auto-category assignment
  - Attempt weight declaration, judge, cancel
  - PlatformRecord creation and conditional update (records vault)
  - Performance-related model methods: best_lift(), total()
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from bot.models.models import (
    AgeCategory,
    Attempt,
    AttemptResult,
    FormulaType,
    Participant,
    ParticipantStatus,
    PlatformRecord,
    Tournament,
    TournamentStatus,
    User,
    WeightCategory,
)
from bot.services.records_service import get_record_count, get_records, update_records_after_tournament
from bot.services.tournament_service import (
    cancel_attempt_result,
    create_categories,
    create_tournament,
    delete_tournament,
    get_tournament,
    get_user,
    judge_attempt,
    list_categories,
    list_participants,
    list_tournaments,
    register_participant,
    set_attempt_weight,
    set_tournament_formula,
    set_tournament_status,
    update_participant_status,
    upsert_user,
)


# ─────────────────────────── Helpers ──────────────────────────────────────────

async def _make_user(session, telegram_id: int = 10001, first_name: str = "Test") -> User:
    user = await upsert_user(session, telegram_id, first_name, "User", "testuser")
    await session.commit()
    return user


async def _make_tournament(session, name: str = "Test Cup", t_type: str = "SBD") -> Tournament:
    t = await create_tournament(session, name, t_type, created_by=10001)
    await session.commit()
    return t


async def _make_participant(
    session, tournament_id: int, user_id: int, **kwargs
) -> Participant:
    defaults = dict(
        full_name="Иванов Иван",
        bodyweight=82.5,
        gender="M",
        age_category="open",
    )
    defaults.update(kwargs)
    p, err = await register_participant(session, tournament_id, user_id, **defaults)
    assert err == "", f"Unexpected registration error: {err}"
    await session.commit()
    return p


# ─────────────────────────── User CRUD ───────────────────────────────────────

class TestUserCRUD:
    async def test_create_user(self, async_session) -> None:
        user = await upsert_user(
            async_session, telegram_id=100, first_name="Ivan",
            last_name="Ivanov", username="ivan"
        )
        await async_session.commit()

        fetched = await get_user(async_session, 100)
        assert fetched is not None
        assert fetched.first_name == "Ivan"
        assert fetched.telegram_id == 100

    async def test_upsert_updates_existing_user(self, async_session) -> None:
        await upsert_user(async_session, 100, "Ivan", "Ivanov", "ivan")
        await async_session.commit()

        await upsert_user(async_session, 100, "Ivan Updated", None, "ivan2")
        await async_session.commit()

        fetched = await get_user(async_session, 100)
        assert fetched.first_name == "Ivan Updated"
        assert fetched.last_name is None
        assert fetched.username == "ivan2"

    async def test_get_nonexistent_user_returns_none(self, async_session) -> None:
        result = await get_user(async_session, 99999)
        assert result is None

    async def test_user_display_name_no_last(self, async_session) -> None:
        user = await upsert_user(async_session, 101, "Maria", None, None)
        assert user.display_name == "Maria"

    async def test_user_display_name_with_last(self, async_session) -> None:
        user = await upsert_user(async_session, 102, "Ivan", "Petrov", None)
        assert user.display_name == "Ivan Petrov"


# ─────────────────────────── Tournament CRUD ──────────────────────────────────

class TestTournamentCRUD:
    async def test_create_and_get_tournament(self, async_session) -> None:
        t = await create_tournament(async_session, "Champions Cup", "SBD", created_by=111)
        await async_session.commit()

        fetched = await get_tournament(async_session, t.id)
        assert fetched is not None
        assert fetched.name == "Champions Cup"
        assert fetched.tournament_type == "SBD"
        assert fetched.status == TournamentStatus.DRAFT

    async def test_get_nonexistent_tournament_returns_none(self, async_session) -> None:
        result = await get_tournament(async_session, 9999)
        assert result is None

    async def test_list_all_tournaments(self, async_session) -> None:
        await create_tournament(async_session, "Cup 1", "SBD", created_by=111)
        await create_tournament(async_session, "Cup 2", "BP", created_by=111)
        await async_session.commit()

        all_t = await list_tournaments(async_session)
        assert len(all_t) == 2

    async def test_list_tournaments_filtered_by_status(self, async_session) -> None:
        t1 = await create_tournament(async_session, "Open Cup", "SBD", created_by=111)
        await create_tournament(async_session, "Draft Cup", "BP", created_by=111)
        await async_session.commit()

        await set_tournament_status(async_session, t1.id, TournamentStatus.REGISTRATION)
        await async_session.commit()

        reg = await list_tournaments(async_session, status=TournamentStatus.REGISTRATION)
        assert len(reg) == 1
        assert reg[0].name == "Open Cup"

    async def test_set_tournament_formula(self, async_session) -> None:
        t = await create_tournament(async_session, "Formula Cup", "SBD", created_by=111)
        await async_session.commit()

        await set_tournament_formula(async_session, t.id, FormulaType.DOTS)
        await async_session.commit()

        fetched = await get_tournament(async_session, t.id, load_relations=False)
        assert fetched.scoring_formula == FormulaType.DOTS

    async def test_delete_tournament_removes_it(self, async_session) -> None:
        t = await create_tournament(async_session, "Temp Cup", "SBD", created_by=111)
        await async_session.commit()
        t_id = t.id

        await delete_tournament(async_session, t_id)
        await async_session.commit()

        fetched = await get_tournament(async_session, t_id, load_relations=False)
        assert fetched is None

    async def test_tournament_lift_types_property(self, async_session) -> None:
        t = await create_tournament(async_session, "BP Cup", "BP", created_by=111)
        assert t.lift_types == ["bench"]

    @pytest.mark.parametrize("t_type,expected_lifts", [
        ("SBD", ["squat", "bench", "deadlift"]),
        ("BP",  ["bench"]),
        ("DL",  ["deadlift"]),
        ("PP",  ["bench", "deadlift"]),
    ])
    async def test_all_tournament_types_have_correct_lifts(
        self, async_session, t_type: str, expected_lifts: list
    ) -> None:
        t = await create_tournament(async_session, "T", t_type, created_by=1)
        assert t.lift_types == expected_lifts


# ─────────────────────────── Weight Categories ────────────────────────────────

class TestWeightCategories:
    async def test_create_and_list_categories(self, async_session) -> None:
        t = await _make_tournament(async_session)
        cats = await create_categories(
            async_session, t.id,
            [("M", "-83"), ("M", "-93"), ("F", "-63")],
        )
        await async_session.commit()
        assert len(cats) == 3

        listed = await list_categories(async_session, t.id)
        names = [c.name for c in listed]
        assert "-83" in names
        assert "-93" in names
        assert "-63" in names

    async def test_create_categories_replaces_existing(self, async_session) -> None:
        t = await _make_tournament(async_session)
        await create_categories(async_session, t.id, [("M", "-83")])
        await async_session.commit()

        # Replace with a different set
        await create_categories(async_session, t.id, [("M", "-93"), ("M", "-105")])
        await async_session.commit()

        listed = await list_categories(async_session, t.id)
        assert len(listed) == 2
        names = [c.name for c in listed]
        assert "-83" not in names

    async def test_category_display_name(self, async_session) -> None:
        t = await _make_tournament(async_session)
        cats = await create_categories(async_session, t.id, [("M", "-93")])
        await async_session.commit()
        assert cats[0].display_name == "-93 кг М"


# ─────────────────────────── Participant Registration ─────────────────────────

class TestParticipantRegistration:
    async def test_register_athlete_success(self, async_session) -> None:
        user = await _make_user(async_session)
        t = await _make_tournament(async_session)

        p, err = await register_participant(
            async_session, t.id, user.id,
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        await async_session.commit()

        assert err == ""
        assert p is not None
        assert p.full_name == "Иванов Иван"
        assert p.bodyweight == 82.5
        assert p.status == ParticipantStatus.REGISTERED

    async def test_duplicate_registration_rejected(self, async_session) -> None:
        user = await _make_user(async_session)
        t = await _make_tournament(async_session)

        await register_participant(
            async_session, t.id, user.id,
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        await async_session.commit()

        p2, err = await register_participant(
            async_session, t.id, user.id,
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        assert p2 is None
        assert err != ""

    async def test_category_auto_assigned_to_smallest_fitting(self, async_session) -> None:
        user = await _make_user(async_session)
        t = await _make_tournament(async_session)
        # Create categories: -83, -93, -105
        await create_categories(
            async_session, t.id,
            [("M", "-83"), ("M", "-93"), ("M", "-105")],
        )
        await async_session.commit()

        p, _ = await register_participant(
            async_session, t.id, user.id,
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        await async_session.commit()

        # 82.5 kg fits -83 (smallest that contains 82.5)
        cat = await async_session.get(WeightCategory, p.category_id)
        assert cat is not None
        assert cat.name == "-83"

    async def test_category_plus_sign_assigned_correctly(self, async_session) -> None:
        user = await _make_user(async_session)
        t = await _make_tournament(async_session)
        await create_categories(
            async_session, t.id,
            [("M", "-105"), ("M", "105+")],
        )
        await async_session.commit()

        p, _ = await register_participant(
            async_session, t.id, user.id,
            full_name="Богатырёв Олег", bodyweight=120.0, gender="M", age_category="open"
        )
        await async_session.commit()

        cat = await async_session.get(WeightCategory, p.category_id)
        assert cat is not None
        assert cat.name == "105+"

    async def test_no_matching_category_results_in_none(self, async_session) -> None:
        user = await _make_user(async_session)
        t = await _make_tournament(async_session)
        # Only female categories — male athlete gets none
        await create_categories(async_session, t.id, [("F", "-63")])
        await async_session.commit()

        p, _ = await register_participant(
            async_session, t.id, user.id,
            full_name="Иванов Иван", bodyweight=62.0, gender="M", age_category="open"
        )
        await async_session.commit()
        assert p.category_id is None

    async def test_list_participants_excludes_withdrawn_by_default(
        self, async_session
    ) -> None:
        user1 = await _make_user(async_session, 10001)
        user2 = await _make_user(async_session, 10002, "Anna")
        t = await _make_tournament(async_session)

        p1, _ = await register_participant(
            async_session, t.id, user1.id, "Иванов Иван", 82.5, "M", "open"
        )
        p2, _ = await register_participant(
            async_session, t.id, user2.id, "Смирнова Анна", 60.0, "F", "open"
        )
        await async_session.commit()

        await update_participant_status(async_session, p2.id, ParticipantStatus.WITHDRAWN)
        await async_session.commit()

        active = await list_participants(async_session, t.id)
        names = [p.full_name for p in active]
        assert "Иванов Иван" in names
        assert "Смирнова Анна" not in names


# ─────────────────────────── Attempt CRUD ────────────────────────────────────

class TestAttemptCRUD:
    async def _setup(self, session) -> Participant:
        user = await _make_user(session, 20001)
        t = await _make_tournament(session, "Scoring Cup")
        p = await _make_participant(session, t.id, user.id)
        return p

    async def test_set_attempt_weight_creates_attempt(self, async_session) -> None:
        p = await self._setup(async_session)

        attempt = await set_attempt_weight(async_session, p.id, "squat", 1, 200.0)
        await async_session.commit()

        assert attempt.weight_kg == 200.0
        assert attempt.lift_type == "squat"
        assert attempt.attempt_number == 1
        assert attempt.result is None

    async def test_judge_attempt_good(self, async_session) -> None:
        p = await self._setup(async_session)
        attempt = await set_attempt_weight(async_session, p.id, "squat", 1, 200.0)
        await async_session.commit()

        judged = await judge_attempt(async_session, attempt.id, AttemptResult.GOOD)
        await async_session.commit()

        assert judged.result == AttemptResult.GOOD
        assert judged.judged_at is not None

    async def test_judge_attempt_bad(self, async_session) -> None:
        p = await self._setup(async_session)
        attempt = await set_attempt_weight(async_session, p.id, "bench", 1, 150.0)
        await async_session.commit()

        judged = await judge_attempt(async_session, attempt.id, AttemptResult.BAD)
        await async_session.commit()

        assert judged.result == AttemptResult.BAD

    async def test_cancel_attempt_result_clears_judgement(self, async_session) -> None:
        p = await self._setup(async_session)
        attempt = await set_attempt_weight(async_session, p.id, "bench", 1, 150.0)
        await async_session.commit()
        await judge_attempt(async_session, attempt.id, AttemptResult.BAD)
        await async_session.commit()

        cancelled = await cancel_attempt_result(async_session, attempt.id)
        await async_session.commit()

        assert cancelled.result is None
        assert cancelled.judged_at is None

    async def test_set_attempt_weight_updates_existing_and_resets_result(
        self, async_session
    ) -> None:
        p = await self._setup(async_session)
        attempt = await set_attempt_weight(async_session, p.id, "deadlift", 1, 220.0)
        await async_session.commit()
        await judge_attempt(async_session, attempt.id, AttemptResult.GOOD)
        await async_session.commit()

        updated = await set_attempt_weight(async_session, p.id, "deadlift", 1, 230.0)
        await async_session.commit()

        assert updated.weight_kg == 230.0
        assert updated.result is None  # resetting weight clears judgement

    async def test_judge_nonexistent_attempt_returns_none(self, async_session) -> None:
        result = await judge_attempt(async_session, 99999, AttemptResult.GOOD)
        assert result is None


# ─────────────────────────── Participant model methods ───────────────────────

class TestParticipantModelMethods:
    """Test best_lift() and total() on ORM Participant objects loaded from DB."""

    async def _full_setup(self, session) -> tuple[Participant, int]:
        """Return (participant, tournament_id) with all three SBD lifts judged.

        All attempt rows are inserted in one batch before any judging begins so
        that selectinload inside judge_attempt always sees the complete attempts
        collection — avoiding SQLAlchemy identity-map stale-cache issues.
        """
        user = await _make_user(session, 30001)
        t = await _make_tournament(session, "Methods Cup", "SBD")
        p = await _make_participant(session, t.id, user.id)

        # Declare all weights first
        a1 = await set_attempt_weight(session, p.id, "squat",    1, 180.0)
        a2 = await set_attempt_weight(session, p.id, "squat",    2, 200.0)
        a3 = await set_attempt_weight(session, p.id, "squat",    3, 205.0)
        a4 = await set_attempt_weight(session, p.id, "bench",    1, 150.0)
        a5 = await set_attempt_weight(session, p.id, "deadlift", 1, 250.0)
        await session.commit()

        # Judge all — at this point every attempt is in DB, so the FIRST
        # selectinload(Participant.attempts) call loads the complete set.
        # Subsequent judge calls update result on the same shared objects.
        await judge_attempt(session, a1.id, AttemptResult.BAD)
        await judge_attempt(session, a2.id, AttemptResult.GOOD)
        await judge_attempt(session, a3.id, AttemptResult.BAD)
        await judge_attempt(session, a4.id, AttemptResult.GOOD)
        await judge_attempt(session, a5.id, AttemptResult.GOOD)
        await session.commit()

        return p, t.id

    async def test_best_lift_returns_highest_good(self, async_session) -> None:
        p, _ = await self._full_setup(async_session)
        # Reload with attempts
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Participant)
            .where(Participant.id == p.id)
            .options(selectinload(Participant.attempts))
        )
        result = await async_session.execute(stmt)
        p_loaded = result.scalar_one()

        assert p_loaded.best_lift("squat") == 200.0  # best of good attempts only
        assert p_loaded.best_lift("bench") == 150.0
        assert p_loaded.best_lift("deadlift") == 250.0

    async def test_total_sums_best_lifts(self, async_session) -> None:
        p, _ = await self._full_setup(async_session)
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Participant)
            .where(Participant.id == p.id)
            .options(selectinload(Participant.attempts))
        )
        result = await async_session.execute(stmt)
        p_loaded = result.scalar_one()

        assert p_loaded.total(["squat", "bench", "deadlift"]) == pytest.approx(600.0)

    async def test_best_lift_returns_none_for_all_bad(self, async_session) -> None:
        user = await _make_user(async_session, 30002)
        t = await _make_tournament(async_session, "Bomb Cup")
        p = await _make_participant(async_session, t.id, user.id)

        a1 = await set_attempt_weight(async_session, p.id, "squat", 1, 200.0)
        await async_session.commit()
        await judge_attempt(async_session, a1.id, AttemptResult.BAD)
        await async_session.commit()

        from sqlalchemy.orm import selectinload
        stmt = (
            select(Participant)
            .where(Participant.id == p.id)
            .options(selectinload(Participant.attempts))
        )
        result = await async_session.execute(stmt)
        p_loaded = result.scalar_one()

        assert p_loaded.best_lift("squat") is None

    async def test_total_returns_none_when_bombed_out(self, async_session) -> None:
        user = await _make_user(async_session, 30003)
        t = await _make_tournament(async_session, "Bomb Cup 2")
        p = await _make_participant(async_session, t.id, user.id)

        # Squat: bombed out
        a1 = await set_attempt_weight(async_session, p.id, "squat", 1, 200.0)
        # Bench: good
        a2 = await set_attempt_weight(async_session, p.id, "bench", 1, 150.0)
        # Deadlift: good
        a3 = await set_attempt_weight(async_session, p.id, "deadlift", 1, 250.0)
        await async_session.commit()
        await judge_attempt(async_session, a1.id, AttemptResult.BAD)
        await judge_attempt(async_session, a2.id, AttemptResult.GOOD)
        await judge_attempt(async_session, a3.id, AttemptResult.GOOD)
        await async_session.commit()

        from sqlalchemy.orm import selectinload
        stmt = (
            select(Participant)
            .where(Participant.id == p.id)
            .options(selectinload(Participant.attempts))
        )
        result = await async_session.execute(stmt)
        p_loaded = result.scalar_one()

        assert p_loaded.total(["squat", "bench", "deadlift"]) is None


# ─────────────────────────── Records Vault CRUD ──────────────────────────────

class TestRecordsVault:
    async def _setup_with_lifts(
        self,
        session,
        squat: float = 200.0,
        bench: float = 150.0,
        deadlift: float = 250.0,
        t_type: str = "SBD",
        telegram_id: int = 40001,
    ) -> tuple[Tournament, Participant]:
        user = await _make_user(session, telegram_id)
        t = await create_tournament(session, "Record Cup", t_type, created_by=99999)
        await session.commit()

        p, _ = await register_participant(
            session, t.id, user.id,
            "Рекордсмен Иван", 82.5, "M", "open"
        )
        await session.commit()

        lift_map = {"squat": squat, "bench": bench, "deadlift": deadlift}
        from bot.models.models import TournamentType
        lifts = TournamentType.LIFTS[t_type]

        # Insert all attempt rows first so that the selectinload in judge_attempt
        # always sees the complete collection — avoids identity-map stale-cache.
        attempt_ids = []
        for lt in lifts:
            a = await set_attempt_weight(session, p.id, lt, 1, lift_map[lt])
            attempt_ids.append(a.id)
        await session.commit()

        for attempt_id in attempt_ids:
            await judge_attempt(session, attempt_id, AttemptResult.GOOD)
        await session.commit()

        return t, p

    async def test_new_records_created_after_tournament(self, async_session) -> None:
        t, _ = await self._setup_with_lifts(async_session)
        records_set = await update_records_after_tournament(async_session, t.id)
        await async_session.commit()

        assert records_set > 0
        count = await get_record_count(async_session)
        assert count > 0

    async def test_sbd_creates_squat_bench_deadlift_and_total(
        self, async_session
    ) -> None:
        t, _ = await self._setup_with_lifts(async_session, 200.0, 150.0, 250.0, "SBD")
        await update_records_after_tournament(async_session, t.id)
        await async_session.commit()

        records = await get_records(async_session, gender="M")
        lift_types = {r.lift_type for r in records}
        # SBD with >1 lift type → also sets a total record
        assert "squat" in lift_types
        assert "bench" in lift_types
        assert "deadlift" in lift_types
        assert "total" in lift_types

    async def test_bp_creates_only_bench_no_total(self, async_session) -> None:
        t, _ = await self._setup_with_lifts(
            async_session, bench=150.0, t_type="BP", telegram_id=40002
        )
        await update_records_after_tournament(async_session, t.id)
        await async_session.commit()

        records = await get_records(async_session, gender="M")
        lift_types = {r.lift_type for r in records}
        assert "bench" in lift_types
        assert "squat" not in lift_types
        assert "total" not in lift_types  # single-lift event

    async def test_record_not_updated_when_lower_weight(self, async_session) -> None:
        # First tournament: sets bench record at 200 kg
        t1, _ = await self._setup_with_lifts(
            async_session, bench=200.0, t_type="BP", telegram_id=40003
        )
        await update_records_after_tournament(async_session, t1.id)
        await async_session.commit()

        # Second tournament: bench only 150 kg — should NOT overwrite the 200 kg record
        user2 = await _make_user(async_session, 40004)
        t2 = await create_tournament(async_session, "Cup 2", "BP", created_by=99999)
        await async_session.commit()
        p2, _ = await register_participant(
            async_session, t2.id, user2.id, "Атлет Два", 82.5, "M", "open"
        )
        await async_session.commit()
        a = await set_attempt_weight(async_session, p2.id, "bench", 1, 150.0)
        await async_session.commit()
        await judge_attempt(async_session, a.id, AttemptResult.GOOD)
        await async_session.commit()

        await update_records_after_tournament(async_session, t2.id)
        await async_session.commit()

        bench_records = await get_records(async_session, gender="M", lift_type="bench")
        # The record must still be 200.0
        assert any(r.weight_kg == 200.0 for r in bench_records)

    async def test_record_updated_when_higher_weight(self, async_session) -> None:
        # First tournament: bench 150 kg
        t1, _ = await self._setup_with_lifts(
            async_session, bench=150.0, t_type="BP", telegram_id=40005
        )
        await update_records_after_tournament(async_session, t1.id)
        await async_session.commit()

        # Second tournament: bench 200 kg — should overwrite
        user2 = await _make_user(async_session, 40006)
        t2 = await create_tournament(async_session, "Cup Better", "BP", created_by=99999)
        await async_session.commit()
        p2, _ = await register_participant(
            async_session, t2.id, user2.id, "Чемпион Два", 82.5, "M", "open"
        )
        await async_session.commit()
        a = await set_attempt_weight(async_session, p2.id, "bench", 1, 200.0)
        await async_session.commit()
        await judge_attempt(async_session, a.id, AttemptResult.GOOD)
        await async_session.commit()

        await update_records_after_tournament(async_session, t2.id)
        await async_session.commit()

        bench_records = await get_records(async_session, gender="M", lift_type="bench")
        assert any(r.weight_kg == 200.0 and r.athlete_name == "Чемпион Два"
                   for r in bench_records)

    async def test_get_records_filter_by_gender(self, async_session) -> None:
        # Male record
        t, _ = await self._setup_with_lifts(
            async_session, bench=200.0, t_type="BP", telegram_id=40007
        )
        await update_records_after_tournament(async_session, t.id)
        await async_session.commit()

        male_records = await get_records(async_session, gender="M")
        female_records = await get_records(async_session, gender="F")
        assert len(male_records) > 0
        assert len(female_records) == 0

    async def test_get_record_count_empty_db(self, async_session) -> None:
        count = await get_record_count(async_session)
        assert count == 0

    async def test_update_records_unknown_tournament_returns_zero(
        self, async_session
    ) -> None:
        records_set = await update_records_after_tournament(async_session, 9999)
        assert records_set == 0
