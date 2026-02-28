"""
Public Records Vault service.

Manages all-time platform records:
  - update_records_after_tournament: scans a finished tournament and updates records
  - get_records: query records with optional filters
  - get_record_count: count records matching filters
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.models import (
    PlatformRecord, Participant, Tournament, TournamentType,
    AgeCategory, RecordLiftType, ParticipantStatus,
)

logger = logging.getLogger(__name__)


async def update_records_after_tournament(
    session: AsyncSession,
    tournament_id: int,
) -> int:
    """
    Scan all participants of a finished tournament and update platform records.

    For each non-withdrawn participant, checks:
      - Individual best lifts (squat, bench, deadlift where applicable)
      - Competition total

    Updates a record if the new performance exceeds the existing one.

    Returns the number of records set or improved.
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Tournament)
        .where(Tournament.id == tournament_id)
    )
    result = await session.execute(stmt)
    tournament = result.scalar_one_or_none()
    if not tournament:
        return 0

    # Load participants with their attempts and categories
    part_stmt = (
        select(Participant)
        .where(
            Participant.tournament_id == tournament_id,
            Participant.status != ParticipantStatus.WITHDRAWN,
        )
        .options(
            selectinload(Participant.attempts),
            selectinload(Participant.category),
        )
    )
    part_result = await session.execute(part_stmt)
    participants = part_result.scalars().all()

    lift_types = TournamentType.LIFTS.get(tournament.tournament_type, [])
    records_set = 0

    for p in participants:
        if not p.age_category:
            continue
        weight_cat = p.category.name if p.category else "open"

        # Check individual lifts
        for lt in lift_types:
            best = p.best_lift(lt)
            if best is None:
                continue
            updated = await _check_and_update_record(
                session=session,
                lift_type=lt,
                weight_kg=best,
                gender=p.gender,
                age_category=p.age_category,
                weight_category_name=weight_cat,
                athlete_name=p.full_name,
                tournament=tournament,
                participant=p,
            )
            if updated:
                records_set += 1

        # Check total (only for SBD — multi-lift events)
        if len(lift_types) > 1:
            total = p.total(lift_types)
            if total is not None:
                updated = await _check_and_update_record(
                    session=session,
                    lift_type=RecordLiftType.TOTAL,
                    weight_kg=total,
                    gender=p.gender,
                    age_category=p.age_category,
                    weight_category_name=weight_cat,
                    athlete_name=p.full_name,
                    tournament=tournament,
                    participant=p,
                )
                if updated:
                    records_set += 1

    logger.info("Records vault: %d records updated for tournament %d", records_set, tournament_id)
    return records_set


async def _check_and_update_record(
    session: AsyncSession,
    lift_type: str,
    weight_kg: float,
    gender: str,
    age_category: str,
    weight_category_name: str,
    athlete_name: str,
    tournament: Tournament,
    participant: Participant,
) -> bool:
    """
    Load existing record for this slot. Create or update if new weight is higher.
    Returns True if a record was set or improved.
    """
    stmt = select(PlatformRecord).where(
        and_(
            PlatformRecord.lift_type == lift_type,
            PlatformRecord.gender == gender,
            PlatformRecord.age_category == age_category,
            PlatformRecord.weight_category_name == weight_category_name,
        )
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        new_record = PlatformRecord(
            lift_type=lift_type,
            weight_kg=weight_kg,
            gender=gender,
            age_category=age_category,
            weight_category_name=weight_category_name,
            athlete_name=athlete_name,
            tournament_id=tournament.id,
            tournament_name=tournament.name,
            participant_id=participant.id,
        )
        session.add(new_record)
        return True

    if weight_kg > existing.weight_kg:
        existing.weight_kg      = weight_kg
        existing.athlete_name   = athlete_name
        existing.tournament_id  = tournament.id
        existing.tournament_name = tournament.name
        existing.participant_id = participant.id
        from sqlalchemy import func
        existing.set_at         = tournament.created_at  # timestamp of the competition
        return True

    return False


async def get_records(
    session: AsyncSession,
    gender: Optional[str] = None,
    age_category: Optional[str] = None,
    weight_category_name: Optional[str] = None,
    lift_type: Optional[str] = None,
) -> List[PlatformRecord]:
    """
    Fetch platform records with optional filters.
    Results are ordered by: gender, age_category, weight_category_name, lift_type.
    """
    conditions = []
    if gender:
        conditions.append(PlatformRecord.gender == gender)
    if age_category:
        conditions.append(PlatformRecord.age_category == age_category)
    if weight_category_name:
        conditions.append(PlatformRecord.weight_category_name == weight_category_name)
    if lift_type:
        conditions.append(PlatformRecord.lift_type == lift_type)

    stmt = select(PlatformRecord)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(
        PlatformRecord.gender,
        PlatformRecord.age_category,
        PlatformRecord.weight_category_name,
        PlatformRecord.lift_type,
    )

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_available_age_categories(session: AsyncSession) -> List[str]:
    """Return distinct age categories that have at least one record."""
    from sqlalchemy import distinct
    stmt = select(distinct(PlatformRecord.age_category)).order_by(PlatformRecord.age_category)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_available_weight_categories(
    session: AsyncSession,
    gender: Optional[str] = None,
    age_category: Optional[str] = None,
) -> List[str]:
    """Return distinct weight category names that have at least one record."""
    from sqlalchemy import distinct
    conditions = []
    if gender:
        conditions.append(PlatformRecord.gender == gender)
    if age_category:
        conditions.append(PlatformRecord.age_category == age_category)

    stmt = select(distinct(PlatformRecord.weight_category_name))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(PlatformRecord.weight_category_name)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_record_count(session: AsyncSession) -> int:
    """Total number of records in the vault."""
    from sqlalchemy import func
    stmt = select(func.count()).select_from(PlatformRecord)
    result = await session.execute(stmt)
    return result.scalar_one()
