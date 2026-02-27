"""
Keyboards for the athlete registration FSM flow.
"""
from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import TournamentCb, MainMenuCb, ParticipantCb
from bot.models.models import Tournament, WeightCategory


def tournament_list_kb(tournaments: List[Tournament]) -> InlineKeyboardMarkup:
    """Show open tournaments for registration selection."""
    builder = InlineKeyboardBuilder()
    for t in tournaments:
        builder.row(
            InlineKeyboardButton(
                text=f"{t.status_emoji} {t.name}  ({t.type_label})",
                callback_data=TournamentCb(action="register_select", tid=t.id).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()


def gender_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨 Мужчины",  callback_data="reg_gender:M"),
        InlineKeyboardButton(text="👩 Женщины",  callback_data="reg_gender:F"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()


def cancel_registration_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()


def confirm_registration_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="reg_confirm"),
        InlineKeyboardButton(text="✏️ Изменить",    callback_data="reg_edit"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()


def my_registrations_kb(participants: list) -> InlineKeyboardMarkup:
    """Athlete's personal registrations list."""
    builder = InlineKeyboardBuilder()
    for p in participants:
        builder.row(
            InlineKeyboardButton(
                text=f"{p.status_emoji} {p.tournament.name}",
                callback_data=ParticipantCb(action="view", pid=p.id, tid=p.tournament_id).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()


def participant_profile_kb(pid: int, can_withdraw: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_withdraw:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Отменить участие",
                callback_data=ParticipantCb(action="withdraw", pid=pid).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=MainMenuCb(action="my_registrations").pack()))
    return builder.as_markup()


def withdraw_confirm_kb(pid: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отменить",
            callback_data=ParticipantCb(action="withdraw_confirm", pid=pid).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=ParticipantCb(action="view", pid=pid).pack(),
        ),
    )
    return builder.as_markup()
