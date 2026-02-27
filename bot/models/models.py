"""
ORM models for SPORTBAZA tournament management system.

Domain overview
---------------
Tournament  — a competition event (type: SBD / BP / DL / PP)
  └─ WeightCategory  — e.g. "-93 кг М"
       └─ Participant — registered athlete (linked to a Telegram User)
            └─ Attempt — individual lift attempt (squat / bench / deadlift)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base

# ─────────────────────────── Constants ────────────────────────────────────────

class TournamentType:
    SBD  = "SBD"   # Squat · Bench · Deadlift  (classic powerlifting)
    BP   = "BP"    # Bench Press only
    DL   = "DL"    # Deadlift only
    PP   = "PP"    # Push-Pull: Bench + Deadlift

    LABELS = {
        SBD: "Троеборье (SBD)",
        BP:  "Жим лёжа",
        DL:  "Становая тяга",
        PP:  "Push-Pull",
    }

    LIFTS: dict[str, list[str]] = {
        SBD: ["squat", "bench", "deadlift"],
        BP:  ["bench"],
        DL:  ["deadlift"],
        PP:  ["bench", "deadlift"],
    }

    LIFT_LABELS: dict[str, str] = {
        "squat":    "Приседания",
        "bench":    "Жим лёжа",
        "deadlift": "Становая тяга",
    }

    LIFT_EMOJI: dict[str, str] = {
        "squat":    "🏋️",
        "bench":    "💪",
        "deadlift": "🔩",
    }


class TournamentStatus:
    DRAFT        = "draft"        # Being configured
    REGISTRATION = "registration" # Open for athlete sign-up
    ACTIVE       = "active"       # Competition in progress
    FINISHED     = "finished"     # Results are final


class ParticipantStatus:
    REGISTERED = "registered"
    CONFIRMED  = "confirmed"
    WITHDRAWN  = "withdrawn"


class AgeCategory:
    SUB_JUNIOR = "sub_junior"  # до 18 лет
    JUNIOR     = "junior"      # 18–23 лет
    OPEN       = "open"        # открытая (без ограничений)
    MASTERS1   = "masters1"    # 40–49 лет
    MASTERS2   = "masters2"    # 50–59 лет
    MASTERS3   = "masters3"    # 60–69 лет
    MASTERS4   = "masters4"    # 70+ лет

    LABELS = {
        "sub_junior": "Юниоры (до 18 лет)",
        "junior":     "Молодёжь (18–23 лет)",
        "open":       "Открытая",
        "masters1":   "Мастера 1 (40–49 лет)",
        "masters2":   "Мастера 2 (50–59 лет)",
        "masters3":   "Мастера 3 (60–69 лет)",
        "masters4":   "Мастера 4 (70+ лет)",
    }


class AttemptResult:
    PENDING = None
    GOOD    = "good"
    BAD     = "bad"

    EMOJI = {
        None:   "⚪️",
        "good": "✅",
        "bad":  "❌",
    }


# ─────────────────────────── Models ───────────────────────────────────────────

class User(Base):
    """Telegram user / potential athlete."""
    __tablename__ = "users"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int]           = mapped_column(BigInteger, unique=True, index=True)
    username:    Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name:  Mapped[str]           = mapped_column(String(255))
    last_name:   Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_admin:    Mapped[bool]          = mapped_column(Boolean, default=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    participants: Mapped[List["Participant"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        parts = [self.first_name]
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts)


class Tournament(Base):
    """A powerlifting / weightlifting event."""
    __tablename__ = "tournaments"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:            Mapped[str]           = mapped_column(String(255))
    tournament_type: Mapped[str]           = mapped_column(String(20))   # TournamentType.*
    status:          Mapped[str]           = mapped_column(String(30), default=TournamentStatus.DRAFT)
    created_by:      Mapped[int]           = mapped_column(BigInteger)   # telegram_id
    created_at:      Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    description:     Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    categories:   Mapped[List["WeightCategory"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    participants: Mapped[List["Participant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )

    @property
    def lift_types(self) -> list[str]:
        return TournamentType.LIFTS.get(self.tournament_type, [])

    @property
    def type_label(self) -> str:
        return TournamentType.LABELS.get(self.tournament_type, self.tournament_type)

    @property
    def status_emoji(self) -> str:
        mapping = {
            TournamentStatus.DRAFT:        "📝",
            TournamentStatus.REGISTRATION: "📋",
            TournamentStatus.ACTIVE:       "🔴",
            TournamentStatus.FINISHED:     "🏆",
        }
        return mapping.get(self.status, "❓")


class WeightCategory(Base):
    """Weight + gender division within a tournament."""
    __tablename__ = "weight_categories"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    name:          Mapped[str] = mapped_column(String(100))   # e.g. "-93", "93+"
    gender:        Mapped[str] = mapped_column(String(5))     # "M" | "F"

    tournament:   Mapped["Tournament"]        = relationship(back_populates="categories")
    participants: Mapped[List["Participant"]] = relationship(back_populates="category")

    @property
    def display_name(self) -> str:
        g = "М" if self.gender == "M" else "Ж"
        return f"{self.name} кг {g}"


class Participant(Base):
    """An athlete registered for a tournament."""
    __tablename__ = "participants"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int]           = mapped_column(ForeignKey("tournaments.id"))
    user_id:       Mapped[int]           = mapped_column(ForeignKey("users.id"))
    full_name:     Mapped[str]           = mapped_column(String(255))
    bodyweight:    Mapped[float]         = mapped_column(Float)
    gender:        Mapped[str]           = mapped_column(String(5))      # "M" | "F"
    age_category:  Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # AgeCategory.*
    category_id:   Mapped[Optional[int]] = mapped_column(ForeignKey("weight_categories.id"), nullable=True)
    status:        Mapped[str]           = mapped_column(String(30), default=ParticipantStatus.REGISTERED)
    lot_number:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    registered_at: Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    user:       Mapped["User"]                  = relationship(back_populates="participants")
    tournament: Mapped["Tournament"]            = relationship(back_populates="participants")
    category:   Mapped[Optional["WeightCategory"]] = relationship(back_populates="participants")
    attempts:   Mapped[List["Attempt"]]         = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )

    def best_lift(self, lift_type: str) -> Optional[float]:
        """Highest successful weight for a given lift type. None if bombed out."""
        goods = [
            a.weight_kg for a in self.attempts
            if a.lift_type == lift_type and a.result == AttemptResult.GOOD and a.weight_kg
        ]
        return max(goods) if goods else None

    def total(self, lift_types: list[str]) -> Optional[float]:
        """
        Sum of best lifts. Returns None if the athlete bombed out on any required lift.
        A bomb-out means zero good attempts AND at least one attempt has been recorded.
        """
        total = 0.0
        for lt in lift_types:
            lifts_of_type = [a for a in self.attempts if a.lift_type == lt]
            if not lifts_of_type:
                # Attempts not entered yet — don't penalise
                continue
            best = self.best_lift(lt)
            if best is None:
                return None  # bombed out
            total += best
        return total

    @property
    def status_emoji(self) -> str:
        mapping = {
            ParticipantStatus.REGISTERED: "⚪️",
            ParticipantStatus.CONFIRMED:  "✅",
            ParticipantStatus.WITHDRAWN:  "❌",
        }
        return mapping.get(self.status, "❓")


class Attempt(Base):
    """
    A single lift attempt.
    Each participant has up to 3 attempts per lift type.
    """
    __tablename__ = "attempts"

    id:             Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int]            = mapped_column(ForeignKey("participants.id"))
    lift_type:      Mapped[str]            = mapped_column(String(30))   # squat / bench / deadlift
    attempt_number: Mapped[int]            = mapped_column(Integer)      # 1, 2, 3
    weight_kg:      Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    result:         Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)  # good / bad / None
    judged_at:      Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="attempts")

    @property
    def result_emoji(self) -> str:
        return AttemptResult.EMOJI.get(self.result, "⚪️")

    @property
    def is_judged(self) -> bool:
        return self.result is not None

    @property
    def display_weight(self) -> str:
        if self.weight_kg is None:
            return "—"
        return f"{self.weight_kg:g} кг"
