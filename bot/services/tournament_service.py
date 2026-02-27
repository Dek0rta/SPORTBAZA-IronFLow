"""
Tournament service — all database operations for tournaments, categories,
participants and attempts.

All functions receive an AsyncSession parameter and are intentionally
pure async functions (no class coupling) for easy unit testing.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.models import (
    User,
    Tournament,
    WeightCategory,
    Participant,
    Attempt,
    TournamentStatus,
    ParticipantStatus,
    AttemptResult,
)


# ── User ──────────────────────────────────────────────────────────────────────

async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: Optional[str],
    username: Optional[str],
) -> User:
    """Create or update a Telegram user record."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        session.add(user)
        await session.flush()
    else:
        user.first_name = first_name
        user.last_name  = last_name
        user.username   = username
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


# ── Tournament ────────────────────────────────────────────────────────────────

async def create_tournament(
    session: AsyncSession,
    name: str,
    tournament_type: str,
    created_by: int,          # telegram_id
    description: Optional[str] = None,
) -> Tournament:
    t = Tournament(
        name=name,
        tournament_type=tournament_type,
        created_by=created_by,
        description=description,
    )
    session.add(t)
    await session.flush()
    return t


async def get_tournament(
    session: AsyncSession,
    tournament_id: int,
    load_relations: bool = True,
) -> Optional[Tournament]:
    q = select(Tournament).where(Tournament.id == tournament_id)
    if load_relations:
        q = q.options(
            selectinload(Tournament.categories),
            selectinload(Tournament.participants).selectinload(Participant.category),
            selectinload(Tournament.participants).selectinload(Participant.attempts),
            selectinload(Tournament.participants).selectinload(Participant.user),
        )
    result = await session.execute(q)
    return result.scalar_one_or_none()


async def list_tournaments(
    session: AsyncSession,
    status: Optional[str] = None,
) -> List[Tournament]:
    q = select(Tournament).order_by(Tournament.created_at.desc())
    if status:
        q = q.where(Tournament.status == status)
    result = await session.execute(q)
    return list(result.scalars().all())


async def list_open_tournaments(session: AsyncSession) -> List[Tournament]:
    """Tournaments visible to athletes (registration open)."""
    return await list_tournaments(session, status=TournamentStatus.REGISTRATION)


async def set_tournament_status(
    session: AsyncSession,
    tournament_id: int,
    status: str,
) -> None:
    await session.execute(
        update(Tournament)
        .where(Tournament.id == tournament_id)
        .values(status=status)
    )


async def delete_tournament(session: AsyncSession, tournament_id: int) -> None:
    await session.execute(
        delete(Tournament).where(Tournament.id == tournament_id)
    )


# ── Weight Categories ─────────────────────────────────────────────────────────

async def create_categories(
    session: AsyncSession,
    tournament_id: int,
    selections: List[Tuple[str, str]],  # [(gender, name), ...]
) -> List[WeightCategory]:
    """Bulk-create categories. Existing categories for the tournament are deleted first."""
    await session.execute(
        delete(WeightCategory).where(WeightCategory.tournament_id == tournament_id)
    )
    cats = [
        WeightCategory(tournament_id=tournament_id, name=name, gender=gender)
        for gender, name in selections
    ]
    session.add_all(cats)
    await session.flush()
    return cats


async def list_categories(
    session: AsyncSession,
    tournament_id: int,
) -> List[WeightCategory]:
    result = await session.execute(
        select(WeightCategory)
        .where(WeightCategory.tournament_id == tournament_id)
        .order_by(WeightCategory.gender, WeightCategory.name)
    )
    return list(result.scalars().all())


# ── Participants ──────────────────────────────────────────────────────────────

async def register_participant(
    session: AsyncSession,
    tournament_id: int,
    user_id: int,         # FK to users.id
    full_name: str,
    bodyweight: float,
    gender: str,
    age_category: Optional[str] = None,
) -> Tuple[Optional[Participant], str]:
    """
    Register athlete for a tournament.
    Returns (participant, error_message). error_message is empty on success.
    """
    # Duplicate check
    existing = await session.execute(
        select(Participant).where(
            Participant.tournament_id == tournament_id,
            Participant.user_id == user_id,
            Participant.status != ParticipantStatus.WITHDRAWN,
        )
    )
    if existing.scalar_one_or_none():
        return None, "Вы уже зарегистрированы на этот турнир."

    # Auto-assign category based on bodyweight + gender
    cats = await list_categories(session, tournament_id)
    category = _assign_category(cats, bodyweight, gender)

    p = Participant(
        tournament_id=tournament_id,
        user_id=user_id,
        full_name=full_name,
        bodyweight=bodyweight,
        gender=gender,
        age_category=age_category,
        category_id=category.id if category else None,
    )
    session.add(p)
    await session.flush()
    return p, ""


def _assign_category(
    categories: List[WeightCategory],
    bodyweight: float,
    gender: str,
) -> Optional[WeightCategory]:
    """
    Auto-assign: find the smallest upper limit that bodyweight fits into.
    IPF convention: "-93" means ≤93 kg; "93+" means >93 kg.
    """
    gender_cats = [c for c in categories if c.gender == gender]
    eligible = []
    for cat in gender_cats:
        name = cat.name
        if name.endswith("+"):
            limit = float(name[:-1])
            if bodyweight > limit:
                eligible.append((float("inf"), cat))
        else:
            limit = float(name.lstrip("-"))
            if bodyweight <= limit:
                eligible.append((limit, cat))
    if not eligible:
        return None
    eligible.sort(key=lambda x: x[0])
    return eligible[0][1]


async def get_participant(
    session: AsyncSession,
    participant_id: int,
) -> Optional[Participant]:
    result = await session.execute(
        select(Participant)
        .where(Participant.id == participant_id)
        .options(
            selectinload(Participant.user),
            selectinload(Participant.tournament),
            selectinload(Participant.category),
            selectinload(Participant.attempts),
        )
    )
    return result.scalar_one_or_none()


async def list_participants(
    session: AsyncSession,
    tournament_id: int,
    include_withdrawn: bool = False,
) -> List[Participant]:
    q = (
        select(Participant)
        .where(Participant.tournament_id == tournament_id)
        .options(
            selectinload(Participant.user),
            selectinload(Participant.category),
            selectinload(Participant.attempts),
        )
        .order_by(Participant.lot_number.asc().nullslast(), Participant.id)
    )
    if not include_withdrawn:
        q = q.where(Participant.status != ParticipantStatus.WITHDRAWN)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_athlete_registrations(
    session: AsyncSession,
    user_id: int,           # users.id (not telegram_id)
) -> List[Participant]:
    result = await session.execute(
        select(Participant)
        .where(Participant.user_id == user_id)
        .options(
            selectinload(Participant.tournament),
            selectinload(Participant.category),
            selectinload(Participant.attempts),
        )
        .order_by(Participant.registered_at.desc())
    )
    return list(result.scalars().all())


async def update_participant_status(
    session: AsyncSession,
    participant_id: int,
    status: str,
) -> None:
    await session.execute(
        update(Participant)
        .where(Participant.id == participant_id)
        .values(status=status)
    )


# ── Attempts ──────────────────────────────────────────────────────────────────

async def set_attempt_weight(
    session: AsyncSession,
    participant_id: int,
    lift_type: str,
    attempt_number: int,
    weight_kg: float,
) -> Attempt:
    """Create or update an attempt's declared weight."""
    result = await session.execute(
        select(Attempt).where(
            Attempt.participant_id == participant_id,
            Attempt.lift_type == lift_type,
            Attempt.attempt_number == attempt_number,
        )
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        attempt = Attempt(
            participant_id=participant_id,
            lift_type=lift_type,
            attempt_number=attempt_number,
            weight_kg=weight_kg,
        )
        session.add(attempt)
    else:
        attempt.weight_kg = weight_kg
        attempt.result = None        # reset any previous result
        attempt.judged_at = None
    await session.flush()
    return attempt


async def judge_attempt(
    session: AsyncSession,
    attempt_id: int,
    result: str,              # AttemptResult.GOOD | BAD
) -> Optional[Attempt]:
    res = await session.execute(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .options(selectinload(Attempt.participant).selectinload(Participant.attempts))
    )
    attempt = res.scalar_one_or_none()
    if attempt:
        attempt.result    = result
        attempt.judged_at = datetime.utcnow()
    return attempt


async def cancel_attempt_result(
    session: AsyncSession,
    attempt_id: int,
) -> Optional[Attempt]:
    res = await session.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = res.scalar_one_or_none()
    if attempt:
        attempt.result    = None
        attempt.judged_at = None
    return attempt
