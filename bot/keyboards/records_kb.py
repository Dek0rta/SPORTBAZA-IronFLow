"""
Keyboards for the Public Records Vault.
Provides inline navigation with gender / age / weight-category filters.
"""
from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import RecordsCb, MainMenuCb
from bot.models.models import AgeCategory


def records_main_kb(record_count: int) -> InlineKeyboardMarkup:
    """Entry screen — filter buttons + back."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👨 Мужчины",
            callback_data=RecordsCb(action="filter_gender", gender="M").pack(),
        ),
        InlineKeyboardButton(
            text="👩 Женщины",
            callback_data=RecordsCb(action="filter_gender", gender="F").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📋 Все рекорды ({record_count})",
            callback_data=RecordsCb(action="list").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data=MainMenuCb(action="main").pack())
    )
    return builder.as_markup()


def records_age_filter_kb(
    gender: str,
    available_age_cats: List[str],
) -> InlineKeyboardMarkup:
    """Age category selection after gender filter."""
    builder = InlineKeyboardBuilder()
    for age_cat in available_age_cats:
        label = AgeCategory.LABELS.get(age_cat, age_cat)
        builder.row(
            InlineKeyboardButton(
                text=f"🏅 {label}",
                callback_data=RecordsCb(
                    action="filter_age",
                    gender=gender,
                    age_cat=age_cat,
                ).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="📋 Все возрасты",
            callback_data=RecordsCb(action="list", gender=gender).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=RecordsCb(action="list").pack(),
        )
    )
    return builder.as_markup()


def records_weight_filter_kb(
    gender: str,
    age_cat: str,
    available_weight_cats: List[str],
) -> InlineKeyboardMarkup:
    """Weight category selection after gender + age filter."""
    builder = InlineKeyboardBuilder()
    row_btns = []
    for wcat in available_weight_cats:
        g = "М" if gender == "M" else "Ж"
        row_btns.append(
            InlineKeyboardButton(
                text=f"{g}{wcat}",
                callback_data=RecordsCb(
                    action="filter_weight",
                    gender=gender,
                    age_cat=age_cat,
                    wcat=wcat,
                ).pack(),
            )
        )
    # 3 per row
    for i in range(0, len(row_btns), 3):
        builder.row(*row_btns[i:i+3])

    builder.row(
        InlineKeyboardButton(
            text="📋 Все весовые",
            callback_data=RecordsCb(action="list", gender=gender, age_cat=age_cat).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=RecordsCb(action="filter_gender", gender=gender).pack(),
        )
    )
    return builder.as_markup()


def records_back_kb(gender: str = "", age_cat: str = "") -> InlineKeyboardMarkup:
    """Navigation back from a results page."""
    builder = InlineKeyboardBuilder()
    if age_cat and gender:
        builder.row(
            InlineKeyboardButton(
                text="🔙 По весу",
                callback_data=RecordsCb(action="filter_age", gender=gender).pack(),
            )
        )
    elif gender:
        builder.row(
            InlineKeyboardButton(
                text="🔙 По возрасту",
                callback_data=RecordsCb(action="filter_gender", gender=gender).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Все рекорды",
            callback_data=RecordsCb(action="reset").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=MainMenuCb(action="main").pack())
    )
    return builder.as_markup()
