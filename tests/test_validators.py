"""
Unit tests — Input validation (validators.py).

Tests Pydantic v2 models for robustness against malformed user input:
  - RegistrationData: full_name, bodyweight, gender, age_category
  - AttemptWeightData: weight_kg (with IPF 0.5-kg rounding rule)

All tests are synchronous; no database session required.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from bot.validators import AttemptWeightData, RegistrationData


# ─────────────────────────── RegistrationData ─────────────────────────────────

class TestRegistrationDataValidName:
    """Full-name field accepts letters (Cyrillic/Latin), spaces and hyphens."""

    def test_cyrillic_two_words(self) -> None:
        d = RegistrationData(
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        assert d.full_name == "Иванов Иван"

    def test_latin_two_words(self) -> None:
        d = RegistrationData(
            full_name="John Doe", bodyweight=82.5, gender="M", age_category="open"
        )
        assert d.full_name == "John Doe"

    def test_hyphenated_surname(self) -> None:
        d = RegistrationData(
            full_name="Иванов-Петров Пётр", bodyweight=65.0, gender="M", age_category="junior"
        )
        assert d.full_name == "Иванов-Петров Пётр"

    def test_leading_trailing_spaces_stripped(self) -> None:
        d = RegistrationData(
            full_name="  Смирнова Анна  ", bodyweight=57.0, gender="F", age_category="open"
        )
        assert d.full_name == "Смирнова Анна"

    def test_minimum_length_two_chars(self) -> None:
        d = RegistrationData(
            full_name="Ли", bodyweight=60.0, gender="M", age_category="open"
        )
        assert d.full_name == "Ли"

    def test_maximum_length_100_chars(self) -> None:
        name = "А" * 50 + " " + "Б" * 49  # 101 chars total with space → must be ≤100
        name = name[:100]
        d = RegistrationData(
            full_name=name, bodyweight=75.0, gender="M", age_category="open"
        )
        assert len(d.full_name) <= 100


class TestRegistrationDataInvalidName:
    def test_too_short_single_char_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(full_name="А", bodyweight=82.5, gender="M", age_category="open")

    def test_too_long_over_100_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="А" * 101, bodyweight=82.5, gender="M", age_category="open"
            )

    def test_digits_in_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Ivan123 Doe", bodyweight=82.5, gender="M", age_category="open"
            )

    def test_special_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Ivan! Doe", bodyweight=82.5, gender="M", age_category="open"
            )

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="", bodyweight=82.5, gender="M", age_category="open"
            )


class TestRegistrationDataBodyweight:
    """Bodyweight must be a float in [30.0, 250.0], rounded to 2 decimal places."""

    @pytest.mark.parametrize("bw", [30.0, 82.5, 150.0, 250.0])
    def test_valid_boundary_and_typical_values(self, bw: float) -> None:
        d = RegistrationData(
            full_name="Иванов Иван", bodyweight=bw, gender="M", age_category="open"
        )
        assert d.bodyweight == pytest.approx(bw)

    def test_rounds_to_two_decimals(self) -> None:
        d = RegistrationData(
            full_name="Иванов Иван", bodyweight=82.567, gender="M", age_category="open"
        )
        assert d.bodyweight == 82.57

    def test_below_minimum_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=25.0, gender="M", age_category="open"
            )

    def test_above_maximum_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=300.0, gender="M", age_category="open"
            )

    def test_negative_bodyweight_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=-10.0, gender="M", age_category="open"
            )

    def test_zero_bodyweight_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=0.0, gender="M", age_category="open"
            )

    def test_string_bodyweight_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight="heavy", gender="M", age_category="open"
            )

    def test_none_bodyweight_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=None, gender="M", age_category="open"
            )


class TestRegistrationDataGender:
    def test_male_gender_accepted(self) -> None:
        d = RegistrationData(
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category="open"
        )
        assert d.gender == "M"

    def test_female_gender_accepted(self) -> None:
        d = RegistrationData(
            full_name="Иванова Мария", bodyweight=57.0, gender="F", age_category="open"
        )
        assert d.gender == "F"

    @pytest.mark.parametrize("bad_gender", ["X", "m", "f", "male", "female", "1", ""])
    def test_invalid_gender_raises(self, bad_gender: str) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=82.5,
                gender=bad_gender, age_category="open"
            )


class TestRegistrationDataAgeCategory:
    @pytest.mark.parametrize("age_cat", [
        "sub_junior", "junior", "open",
        "masters1", "masters2", "masters3", "masters4",
    ])
    def test_all_valid_age_categories_accepted(self, age_cat: str) -> None:
        d = RegistrationData(
            full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category=age_cat
        )
        assert d.age_category == age_cat

    @pytest.mark.parametrize("bad_cat", ["veteran", "elite", "open_", "senior", "0", ""])
    def test_invalid_age_category_raises(self, bad_cat: str) -> None:
        with pytest.raises(ValidationError):
            RegistrationData(
                full_name="Иванов Иван", bodyweight=82.5, gender="M", age_category=bad_cat
            )


# ─────────────────────────── AttemptWeightData ────────────────────────────────

class TestAttemptWeightDataValid:
    @pytest.mark.parametrize("w", [20.0, 100.0, 200.5, 500.0])
    def test_valid_weights(self, w: float) -> None:
        d = AttemptWeightData(weight_kg=w)
        assert d.weight_kg == pytest.approx(w)

    def test_rounds_up_to_nearest_half(self) -> None:
        # 100.3 × 2 = 200.6 → round → 201 → /2 = 100.5
        d = AttemptWeightData(weight_kg=100.3)
        assert d.weight_kg == 100.5

    def test_rounds_down_to_nearest_half(self) -> None:
        # 100.2 × 2 = 200.4 → round → 200 → /2 = 100.0
        d = AttemptWeightData(weight_kg=100.2)
        assert d.weight_kg == 100.0

    def test_exact_half_kg_unchanged(self) -> None:
        d = AttemptWeightData(weight_kg=182.5)
        assert d.weight_kg == 182.5

    def test_exact_integer_kg_unchanged(self) -> None:
        d = AttemptWeightData(weight_kg=220.0)
        assert d.weight_kg == 220.0

    def test_boundary_min_20(self) -> None:
        d = AttemptWeightData(weight_kg=20.0)
        assert d.weight_kg == 20.0

    def test_boundary_max_500(self) -> None:
        d = AttemptWeightData(weight_kg=500.0)
        assert d.weight_kg == 500.0


class TestAttemptWeightDataInvalid:
    def test_below_minimum_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=15.0)

    def test_above_maximum_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=600.0)

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=-50.0)

    def test_zero_weight_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=0.0)

    def test_string_weight_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg="heavy")

    def test_none_weight_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=None)

    def test_list_weight_raises(self) -> None:
        with pytest.raises(ValidationError):
            AttemptWeightData(weight_kg=[100.0])
