"""
Keyboards for admin panel: tournament management and participant control.
"""
from typing import List, Set

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import (
    AdminPanelCb,
    TournamentCb,
    CategoryCb,
    ParticipantCb,
    MainMenuCb,
)
from bot.models.models import Tournament, TournamentStatus, Participant, ParticipantStatus

# ── Tournament lists ──────────────────────────────────────────────────────────

def tournament_list_admin_kb(tournaments: List[Tournament]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tournaments:
        builder.row(
            InlineKeyboardButton(
                text=f"{t.status_emoji} {t.name}  [{t.type_label}]",
                callback_data=TournamentCb(action="view", tid=t.id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ Создать турнир", callback_data=TournamentCb(action="create").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад",          callback_data=AdminPanelCb(action="back").pack()),
    )
    return builder.as_markup()


def tournament_detail_admin_kb(t: Tournament) -> InlineKeyboardMarkup:
    """Context-aware control panel for a single tournament."""
    builder = InlineKeyboardBuilder()

    if t.status == TournamentStatus.DRAFT:
        builder.row(
            InlineKeyboardButton(
                text="📋 Открыть регистрацию",
                callback_data=TournamentCb(action="open_reg", tid=t.id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=TournamentCb(action="delete_confirm", tid=t.id).pack(),
            )
        )

    elif t.status == TournamentStatus.REGISTRATION:
        builder.row(
            InlineKeyboardButton(
                text="▶️ Начать соревнование",
                callback_data=TournamentCb(action="start", tid=t.id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="👥 Участники",
                callback_data=ParticipantCb(action="list", tid=t.id).pack(),
            )
        )

    elif t.status == TournamentStatus.ACTIVE:
        builder.row(
            InlineKeyboardButton(
                text="⚡ Судейство",
                callback_data=ParticipantCb(action="select_scoring", tid=t.id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🏁 Завершить турнир",
                callback_data=TournamentCb(action="finish_confirm", tid=t.id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="👥 Участники",
                callback_data=ParticipantCb(action="list", tid=t.id).pack(),
            )
        )

    elif t.status == TournamentStatus.FINISHED:
        builder.row(
            InlineKeyboardButton(
                text="📤 Экспорт в Google Sheets",
                callback_data=TournamentCb(action="export", tid=t.id).pack(),
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data=TournamentCb(action="list").pack()))
    return builder.as_markup()


def confirm_action_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=yes_cb),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_cb),
    )
    return builder.as_markup()


# ── Category selector (multi-toggle) ─────────────────────────────────────────

# Predefined IPF-style category sets
PREDEFINED_CATEGORIES = {
    "M": ["-59", "-66", "-74", "-83", "-93", "-105", "-120", "120+"],
    "F": ["-47", "-52", "-57", "-63", "-69", "-76", "-84", "84+"],
}


def category_setup_kb(
    tid: int,
    selected: Set[str],   # e.g. {"M:-93", "M:-83", "F:-63"}
) -> InlineKeyboardMarkup:
    """Multi-toggle category selector for tournament setup."""
    builder = InlineKeyboardBuilder()

    for gender, cats in PREDEFINED_CATEGORIES.items():
        g_label = "М" if gender == "M" else "Ж"
        for cat in cats:
            key = f"{gender}:{cat}"
            checked = "☑️" if key in selected else "☐"
            builder.row(
                InlineKeyboardButton(
                    text=f"{checked} {g_label} {cat} кг",
                    callback_data=CategoryCb(
                        action="toggle", tid=tid, gender=gender, cid=0
                    ).pack()
                    # We embed the category name via a raw callback for brevity
                    # Overriding with raw string for tight size:
                )
            )

    # Use raw callback data strings for category toggles to stay <64 bytes
    # Rebuild without CallbackData factory for row-level buttons:
    builder = InlineKeyboardBuilder()
    for gender, cats in PREDEFINED_CATEGORIES.items():
        g_label = "М" if gender == "M" else "Ж"
        row_buttons = []
        for cat in cats:
            key = f"{gender}:{cat}"
            checked = "☑️" if key in selected else "☐"
            row_buttons.append(
                InlineKeyboardButton(
                    text=f"{checked} {g_label}{cat}",
                    callback_data=f"cat_toggle:{tid}:{gender}:{cat}",
                )
            )
        # 4 per row
        for i in range(0, len(row_buttons), 4):
            builder.row(*row_buttons[i:i+4])

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить категории",
            callback_data="categories_confirm",   # plain string — avoids empty-field parsing issues
        )
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=TournamentCb(action="list").pack()))
    return builder.as_markup()


# ── Participant list (admin) ──────────────────────────────────────────────────

def participant_list_kb(participants: List[Participant], tid: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in participants:
        cat = p.category.display_name if p.category else "без категории"
        builder.row(
            InlineKeyboardButton(
                text=f"{p.status_emoji} {p.full_name} ({p.bodyweight:g} кг) — {cat}",
                # Use admin-specific action to avoid conflict with athlete "view"
                callback_data=ParticipantCb(action="admin_view", pid=p.id, tid=tid).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=TournamentCb(action="view", tid=tid).pack()))
    return builder.as_markup()


def participant_detail_admin_kb(p: Participant) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if p.status == ParticipantStatus.REGISTERED:
        builder.row(
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=ParticipantCb(action="admin_confirm", pid=p.id, tid=p.tournament_id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🚫 Снять с соревнования",
            callback_data=ParticipantCb(action="admin_withdraw", pid=p.id, tid=p.tournament_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку",
            callback_data=ParticipantCb(action="list", tid=p.tournament_id).pack(),
        )
    )
    return builder.as_markup()


def scoring_participant_list_kb(participants: List[Participant], tid: int) -> InlineKeyboardMarkup:
    """Select a participant to judge in the scoring panel."""
    builder = InlineKeyboardBuilder()
    for p in participants:
        builder.row(
            InlineKeyboardButton(
                text=f"#{p.lot_number or '?'} {p.full_name}",
                callback_data=ParticipantCb(action="scoring", pid=p.id, tid=tid).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=TournamentCb(action="view", tid=tid).pack()))
    return builder.as_markup()
