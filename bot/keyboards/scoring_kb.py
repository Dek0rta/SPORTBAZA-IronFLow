"""
Live scoring keyboard — the digital judges' panel.

Layout for each attempt:
  ┌──────────────────────────────────────────┐
  │  ⚖️ 200 кг   [✅ ЗАЧЁТ]  [❌ НЕ ЗАЧЁТ] │  ← unjudged with weight
  │  ⚖️ —        [📝 Вес]                   │  ← no weight yet
  │  ✅ 210 кг   [↩ Отменить]               │  ← already judged
  └──────────────────────────────────────────┘
"""
from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import AttemptCb, ScoringNavCb, ParticipantCb
from bot.models.models import Attempt, AttemptResult, TournamentType


def scoring_panel_kb(
    attempts: List[Attempt],
    lift_types: List[str],
    participant_id: int,
    tournament_id: int,
    prev_pid: Optional[int],
    next_pid: Optional[int],
) -> InlineKeyboardMarkup:
    """
    Build the full scoring keyboard for one participant.
    Groups buttons by lift type.
    """
    builder = InlineKeyboardBuilder()

    attempt_map: dict[tuple[str, int], Attempt] = {
        (a.lift_type, a.attempt_number): a for a in attempts
    }

    for lift in lift_types:
        lift_label = TournamentType.LIFT_LABELS.get(lift, lift.capitalize())
        lift_emoji = TournamentType.LIFT_EMOJI.get(lift, "🏋️")

        # Section separator row (non-clickable)
        builder.row(
            InlineKeyboardButton(
                text=f"── {lift_emoji} {lift_label} ──",
                callback_data="noop",
            )
        )

        for num in (1, 2, 3):
            attempt = attempt_map.get((lift, num))
            row_buttons = _attempt_buttons(attempt, lift, num, participant_id)
            builder.row(*row_buttons)

    # Navigation
    nav_row = []
    if prev_pid:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Пред.",
                callback_data=ScoringNavCb(action="prev", tid=tournament_id, pid=prev_pid).pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text="📋 Список",
            callback_data=ScoringNavCb(action="list", tid=tournament_id, pid=participant_id).pack(),
        )
    )
    if next_pid:
        nav_row.append(
            InlineKeyboardButton(
                text="▶️ След.",
                callback_data=ScoringNavCb(action="next", tid=tournament_id, pid=next_pid).pack(),
            )
        )
    builder.row(*nav_row)

    return builder.as_markup()


def _attempt_buttons(
    attempt: Optional[Attempt],
    lift_type: str,
    attempt_number: int,
    participant_id: int,
) -> List[InlineKeyboardButton]:
    """Return the button row for a single attempt slot."""
    label_prefix = f"П{attempt_number}"

    if attempt is None:
        # Slot not yet created — offer to set weight
        return [
            InlineKeyboardButton(
                text=f"⚖️ {label_prefix}: задать вес",
                callback_data=f"att_new:{participant_id}:{lift_type}:{attempt_number}",
            )
        ]

    if attempt.weight_kg is None:
        return [
            InlineKeyboardButton(
                text=f"⚖️ {label_prefix}: задать вес",
                callback_data=f"att_new:{participant_id}:{lift_type}:{attempt_number}",
            )
        ]

    weight_str = f"{attempt.weight_kg:g} кг"

    if not attempt.is_judged:
        return [
            InlineKeyboardButton(
                text=f"⚖️ {label_prefix} {weight_str}",
                callback_data=f"att_new:{participant_id}:{lift_type}:{attempt_number}",
            ),
            InlineKeyboardButton(
                text="✅ Зачёт",
                callback_data=AttemptCb(action="good", aid=attempt.id, pid=participant_id).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Не зачёт",
                callback_data=AttemptCb(action="bad", aid=attempt.id, pid=participant_id).pack(),
            ),
        ]

    # Already judged
    result_icon = "✅" if attempt.result == AttemptResult.GOOD else "❌"
    return [
        InlineKeyboardButton(
            text=f"{result_icon} {label_prefix} {weight_str}",
            callback_data="noop",
        ),
        InlineKeyboardButton(
            text="↩️ Отменить",
            callback_data=AttemptCb(action="cancel_result", aid=attempt.id, pid=participant_id).pack(),
        ),
    ]


def cancel_input_kb(participant_id: int, tournament_id: int) -> InlineKeyboardMarkup:
    """Shown while waiting for weight text input."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=ParticipantCb(action="scoring", pid=participant_id, tid=tournament_id).pack(),
        )
    )
    return builder.as_markup()
