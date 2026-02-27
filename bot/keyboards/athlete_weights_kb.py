"""
Keyboard for the athlete weight-declaration panel.

Each attempt slot is a button. Tapping it starts the FSM weight-input flow.
Layout mirrors the admin scoring panel so athletes see the same structure.
"""
from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import ParticipantCb, MainMenuCb
from bot.models.models import Attempt, AttemptResult, TournamentType


def declare_weights_kb(
    attempts: List[Attempt],
    lift_types: List[str],
    participant_id: int,
    can_edit: bool = True,       # False when tournament is active and attempt is judged
) -> InlineKeyboardMarkup:
    """
    Build the weight-declaration keyboard for a participant.
    Each unjudged attempt slot is a tappable button.
    """
    builder = InlineKeyboardBuilder()

    attempt_map: dict[tuple[str, int], Attempt] = {
        (a.lift_type, a.attempt_number): a for a in attempts
    }

    for lift in lift_types:
        lift_label = TournamentType.LIFT_LABELS.get(lift, lift.capitalize())
        lift_emoji = TournamentType.LIFT_EMOJI.get(lift, "🏋️")

        # Section header (non-clickable)
        builder.row(
            InlineKeyboardButton(
                text=f"── {lift_emoji} {lift_label} ──",
                callback_data="noop",
            )
        )

        row = []
        for num in (1, 2, 3):
            attempt = attempt_map.get((lift, num))
            row.append(_slot_button(attempt, lift, num, participant_id, can_edit))
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к профилю",
            callback_data=ParticipantCb(action="view", pid=participant_id).pack(),
        )
    )
    return builder.as_markup()


def _slot_button(
    attempt: Optional[Attempt],
    lift_type: str,
    attempt_number: int,
    participant_id: int,
    can_edit: bool,
) -> InlineKeyboardButton:
    """Build a single attempt slot button."""
    label = f"П{attempt_number}"

    # Already judged — show result, not editable by athlete
    if attempt and attempt.is_judged:
        icon = "✅" if attempt.result == AttemptResult.GOOD else "❌"
        return InlineKeyboardButton(
            text=f"{icon} {label}: {attempt.display_weight}",
            callback_data="noop",
        )

    # Weight declared, not yet judged
    if attempt and attempt.weight_kg:
        weight_str = f"{attempt.weight_kg:g}"
        if can_edit:
            return InlineKeyboardButton(
                text=f"✏️ {label}: {weight_str}кг",
                callback_data=f"adeclare:{participant_id}:{lift_type}:{attempt_number}",
            )
        return InlineKeyboardButton(
            text=f"⚪️ {label}: {weight_str}кг",
            callback_data="noop",
        )

    # No weight yet
    if can_edit:
        return InlineKeyboardButton(
            text=f"➕ {label}: —",
            callback_data=f"adeclare:{participant_id}:{lift_type}:{attempt_number}",
        )
    return InlineKeyboardButton(text=f"⚪️ {label}: —", callback_data="noop")


def cancel_weight_input_kb(participant_id: int) -> InlineKeyboardMarkup:
    """Shown while waiting for weight text input."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"aweights_panel:{participant_id}",
        )
    )
    return builder.as_markup()
