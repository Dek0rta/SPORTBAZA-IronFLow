"""
Shared pytest fixtures for SPORTBAZA tests.

Sets required environment variables BEFORE any bot module is imported so that
pydantic-settings and SQLAlchemy engine initialisation use safe test values.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

# ── Set env vars before any bot import ────────────────────────────────────────
os.environ.setdefault("BOT_TOKEN", "test-token-for-pytest")
os.environ.setdefault("ADMIN_IDS", "123456789")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# ── Third-party ───────────────────────────────────────────────────────────────
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Bot imports (safe after env vars are set) ──────────────────────────────────
from bot.models.base import Base


# ── DB fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a fresh AsyncSession backed by an isolated in-memory SQLite database.
    Schema is created fresh for every test function; engine is always disposed
    on teardown, even if the test raises an exception.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


# ── Mock helpers ──────────────────────────────────────────────────────────────

class _MockAttempt:
    """Minimal attempt object for ranking engine tests (no DB required)."""

    def __init__(self, lift_type: str, weight_kg: float, result: str = "good") -> None:
        self.lift_type  = lift_type
        self.weight_kg  = weight_kg
        self.result     = result


class _MockParticipant:
    """
    Minimal participant object for ranking engine tests.

    Replicates the interface used by ranking_service (best_lift / total methods)
    without requiring a database session or full ORM setup.
    """

    def __init__(
        self,
        full_name: str,
        bodyweight: float,
        gender: str,
        age_category: str = "open",
    ) -> None:
        self.full_name    = full_name
        self.bodyweight   = bodyweight
        self.gender       = gender
        self.age_category = age_category
        self.category_id  = None
        self.category     = None
        self.attempts: list[_MockAttempt] = []

    def add_attempt(self, lift_type: str, weight_kg: float, result: str = "good") -> None:
        self.attempts.append(_MockAttempt(lift_type, weight_kg, result))

    def best_lift(self, lift_type: str) -> float | None:
        goods = [
            a.weight_kg for a in self.attempts
            if a.lift_type == lift_type and a.result == "good" and a.weight_kg
        ]
        return max(goods) if goods else None

    def total(self, lift_types: list[str]) -> float | None:
        result = 0.0
        for lt in lift_types:
            lifts = [a for a in self.attempts if a.lift_type == lt]
            if not lifts:
                continue
            best = self.best_lift(lt)
            if best is None:
                return None
            result += best
        return result


@pytest.fixture
def make_participant():
    """Factory fixture — returns a callable that builds a _MockParticipant."""
    return _MockParticipant
