"""
Public Records Vault handler.

Accessible to all users via:
  - /records command
  - "🥇 База рекордов" button in athlete main menu

Provides inline navigation with gender / age / weight-category filters.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    MainMenuCb, RecordsCb,
    records_main_kb, records_age_filter_kb,
    records_weight_filter_kb, records_back_kb,
)
from bot.models.models import AgeCategory, RecordLiftType
from bot.services.records_service import (
    get_records, get_record_count,
    get_available_age_categories, get_available_weight_categories,
)

logger = logging.getLogger(__name__)
router = Router(name="records")

_PAGE_SIZE = 20   # max records shown per message before truncation


# ── Entry points ──────────────────────────────────────────────────────────────

@router.message(Command("records"))
async def cmd_records(message: Message, session: AsyncSession) -> None:
    count = await get_record_count(session)
    await message.answer(
        _vault_header(count),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_main_kb(count),
    )


@router.callback_query(MainMenuCb.filter(F.action == "records"))
async def cq_records_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    count = await get_record_count(session)
    await callback.message.edit_text(
        _vault_header(count),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_main_kb(count),
    )
    await callback.answer()


@router.callback_query(RecordsCb.filter(F.action == "reset"))
async def cq_records_reset(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    count = await get_record_count(session)
    await callback.message.edit_text(
        _vault_header(count),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_main_kb(count),
    )
    await callback.answer()


# ── Gender filter ─────────────────────────────────────────────────────────────

@router.callback_query(RecordsCb.filter(F.action == "filter_gender"))
async def cq_filter_gender(
    callback: CallbackQuery,
    callback_data: RecordsCb,
    session: AsyncSession,
) -> None:
    gender = callback_data.gender
    age_cats = await get_available_age_categories(session)
    # Filter to only those that have records for this gender
    from bot.models.models import PlatformRecord
    from sqlalchemy import select, distinct, and_
    stmt = select(distinct(PlatformRecord.age_category)).where(
        PlatformRecord.gender == gender
    ).order_by(PlatformRecord.age_category)
    result = await session.execute(stmt)
    age_cats = [row[0] for row in result.all()]

    if not age_cats:
        await callback.answer("Рекордов для этой категории пока нет.", show_alert=True)
        return

    g_label = "Мужчины" if gender == "M" else "Женщины"
    await callback.message.edit_text(
        f"🥇 *База рекордов — {g_label}*\n\nВыберите возрастную категорию:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_age_filter_kb(gender, age_cats),
    )
    await callback.answer()


# ── Age filter ────────────────────────────────────────────────────────────────

@router.callback_query(RecordsCb.filter(F.action == "filter_age"))
async def cq_filter_age(
    callback: CallbackQuery,
    callback_data: RecordsCb,
    session: AsyncSession,
) -> None:
    gender   = callback_data.gender
    age_cat  = callback_data.age_cat

    weight_cats = await get_available_weight_categories(session, gender=gender, age_category=age_cat)
    if not weight_cats:
        await callback.answer("Нет рекордов для этой категории.", show_alert=True)
        return

    g_label   = "Мужчины" if gender == "M" else "Женщины"
    age_label = AgeCategory.LABELS.get(age_cat, age_cat)
    await callback.message.edit_text(
        f"🥇 *{g_label} · {age_label}*\n\nВыберите весовую категорию:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_weight_filter_kb(gender, age_cat, weight_cats),
    )
    await callback.answer()


# ── Weight filter (final list) ────────────────────────────────────────────────

@router.callback_query(RecordsCb.filter(F.action == "filter_weight"))
async def cq_filter_weight(
    callback: CallbackQuery,
    callback_data: RecordsCb,
    session: AsyncSession,
) -> None:
    gender   = callback_data.gender
    age_cat  = callback_data.age_cat
    wcat     = callback_data.wcat

    records = await get_records(
        session,
        gender=gender,
        age_category=age_cat,
        weight_category_name=wcat,
    )
    if not records:
        await callback.answer("Рекордов пока нет.", show_alert=True)
        return

    g_label   = "М" if gender == "M" else "Ж"
    age_label = AgeCategory.LABELS.get(age_cat, age_cat)
    text = f"🥇 *Рекорды: {g_label}{wcat} · {age_label}*\n\n"
    text += _format_records_table(records)

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_back_kb(gender=gender, age_cat=age_cat),
    )
    await callback.answer()


# ── Full list (no weight filter) ──────────────────────────────────────────────

@router.callback_query(RecordsCb.filter(F.action == "list"))
async def cq_records_list(
    callback: CallbackQuery,
    callback_data: RecordsCb,
    session: AsyncSession,
) -> None:
    gender  = callback_data.gender or None
    age_cat = callback_data.age_cat or None

    records = await get_records(session, gender=gender, age_category=age_cat)
    if not records:
        await callback.answer("Рекордов пока нет.", show_alert=True)
        return

    gender_label = ("Мужчины" if gender == "M" else "Женщины") if gender else "Все"
    age_label    = AgeCategory.LABELS.get(age_cat, age_cat) if age_cat else "Все категории"
    text = f"🥇 *База рекордов — {gender_label} · {age_label}*\n\n"
    text += _format_records_table(records[:_PAGE_SIZE])
    if len(records) > _PAGE_SIZE:
        text += f"\n_…и ещё {len(records) - _PAGE_SIZE} рекордов. Используйте фильтры для уточнения._"

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=records_back_kb(gender=gender or "", age_cat=age_cat or ""),
    )
    await callback.answer()


# ── Formatting helpers ────────────────────────────────────────────────────────

def _vault_header(count: int) -> str:
    return (
        f"🏛️ *SPORTBAZA — База рекордов платформы*\n\n"
        f"Здесь хранятся лучшие результаты за всё время.\n"
        f"Всего рекордов в базе: *{count}*\n\n"
        f"Выберите фильтр для просмотра:"
    )


def _format_records_table(records) -> str:
    """Render records as a Markdown table grouped by age + weight category."""
    lines = []
    current_group = None

    for r in records:
        group_key = (r.gender, r.age_category, r.weight_category_name)
        if group_key != current_group:
            current_group = group_key
            g = "М" if r.gender == "M" else "Ж"
            age_lbl = AgeCategory.LABELS.get(r.age_category, r.age_category)
            lines.append(f"\n*📂 {g}{r.weight_category_name} кг · {age_lbl}*")
            lines.append("─────────────────")

        lift_emoji = {
            "squat":    "🏋️",
            "bench":    "💪",
            "deadlift": "🔩",
            "total":    "🏆",
        }.get(r.lift_type, "•")
        lift_lbl = RecordLiftType.LABELS.get(r.lift_type, r.lift_type)
        lines.append(
            f"{lift_emoji} *{lift_lbl}*: `{r.weight_kg:g} кг` — {r.athlete_name} "
            f"_({r.tournament_name}, {r.set_at.strftime('%d.%m.%Y')})_"
        )

    return "\n".join(lines) if lines else "_Рекордов пока нет._"
