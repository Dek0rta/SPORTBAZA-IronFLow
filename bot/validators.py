"""
Input validation for FSM text handlers — Pydantic v2 models.

Used to validate user-supplied text before writing to the database.
Keeps validation logic out of handler code and makes it trivially testable.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

# Allow Cyrillic, Latin, spaces and hyphens; at least two characters
_NAME_RE = re.compile(
    r"^[А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]*[А-ЯЁа-яёA-Za-z]$"
)


class RegistrationData(BaseModel):
    """
    Athlete registration payload validated before writing to DB.

    Attributes
    ----------
    full_name    : Full athlete name (2–100 chars, letters / spaces / hyphens)
    bodyweight   : Body weight in kg (30.0–250.0)
    gender       : "M" or "F"
    age_category : One of AgeCategory.*
    """

    full_name: str
    bodyweight: float
    gender: Literal["M", "F"]
    age_category: Literal[
        "sub_junior", "junior", "open",
        "masters1", "masters2", "masters3", "masters4",
    ]

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Имя должно содержать от 2 до 100 символов")
        if not _NAME_RE.match(v):
            raise ValueError(
                "Имя должно содержать только буквы (рус/лат), пробелы и дефисы"
            )
        return v

    @field_validator("bodyweight")
    @classmethod
    def validate_bodyweight(cls, v: float) -> float:
        if v < 30.0 or v > 250.0:
            raise ValueError("Собственный вес должен быть в диапазоне 30–250 кг")
        return round(v, 2)


class AttemptWeightData(BaseModel):
    """
    Single lift attempt weight validated before being stored.

    Attributes
    ----------
    weight_kg : Declared attempt weight in kg (20.0–500.0)
    """

    weight_kg: float

    @field_validator("weight_kg")
    @classmethod
    def validate_weight_kg(cls, v: float) -> float:
        if v < 20.0 or v > 500.0:
            raise ValueError("Вес подхода должен быть в диапазоне 20–500 кг")
        # IPF rule: weights must be multiples of 0.5 kg — round to nearest half
        return round(v * 2) / 2
