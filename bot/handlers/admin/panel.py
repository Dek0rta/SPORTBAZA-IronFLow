"""
Admin panel entry point and participant management.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    AdminPanelCb, ParticipantCb, TournamentCb,
    admin_main_menu, participant_list_kb, participant_detail_admin_kb,
    scoring_participant_list_kb,
)
from bot.middlewares import IsAdmin
from bot.models.models import ParticipantStatus, AgeCategory
from bot.services import (
    list_tournaments, list_participants, get_participant, update_participant_status,
)
from bot.services.notification_service import notify_registration_confirmed, create_db_notification

logger = logging.getLogger(__name__)
router = Router(name="admin_panel")
router.callback_query.filter(IsAdmin())


# ── Admin home (back) ─────────────────────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "back"))
async def cq_admin_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "⚡ *Панель администратора*\n\nВыберите раздел:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_menu(),
    )
    await callback.answer()


# ── Participants ──────────────────────────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "participants"))
async def cq_participants_choose_tournament(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    tournaments = await list_tournaments(session)
    if not tournaments:
        await callback.answer("Нет турниров.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for t in tournaments:
        builder.row(InlineKeyboardButton(
            text=f"{t.status_emoji} {t.name}",
            callback_data=ParticipantCb(action="list", tid=t.id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="back").pack()
    ))
    await callback.message.edit_text(
        "👥 *Выберите турнир:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(ParticipantCb.filter(F.action == "list"))
async def cq_participant_list(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    participants = await list_participants(session, callback_data.tid)
    if not participants:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        back_kb = InlineKeyboardBuilder()
        back_kb.row(InlineKeyboardButton(
            text="🔙 Назад к турниру",
            callback_data=TournamentCb(action="view", tid=callback_data.tid).pack(),
        ))
        await callback.message.edit_text(
            "👥 *Участники*\n\n_Нет участников._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_kb.as_markup(),
        )
        await callback.answer()
        return

    text = f"👥 *Участники* — `{len(participants)}`"
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=participant_list_kb(participants, callback_data.tid),
    )
    await callback.answer()


@router.callback_query(ParticipantCb.filter(F.action == "admin_view"))
async def cq_participant_detail_admin(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    cat     = p.category.display_name if p.category else "не назначена"
    age_cat = AgeCategory.LABELS.get(p.age_category, "—") if p.age_category else "—"
    lot_str = f"#{p.lot_number}" if p.lot_number else "—"
    text = (
        f"👤 *{p.full_name}*\n\n"
        f"🏆 Турнир: {p.tournament.name}\n"
        f"⚖️ Вес: `{p.bodyweight:g} кг`\n"
        f"📂 Весовая категория: {cat}\n"
        f"🏅 Возрастная категория: {age_cat}\n"
        f"🎲 Жребий: `{lot_str}`\n"
        f"📌 Статус: {p.status_emoji} {p.status}\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=participant_detail_admin_kb(p),
    )
    await callback.answer()


@router.callback_query(ParticipantCb.filter(F.action == "admin_confirm"))
async def cq_confirm_participant(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    await update_participant_status(session, p.id, ParticipantStatus.CONFIRMED)
    await notify_registration_confirmed(callback.bot, p)
    await create_db_notification(
        session, p.user_id, "confirmed",
        "Заявка подтверждена",
        f"Ваша заявка на «{p.tournament.name}» подтверждена. Удачи! 💪",
    )

    await callback.answer("✅ Участник подтверждён!")
    # Refresh view
    participants = await list_participants(session, callback_data.tid)
    await callback.message.edit_text(
        f"👥 *Участники* — `{len(participants)}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=participant_list_kb(participants, callback_data.tid),
    )


@router.callback_query(ParticipantCb.filter(F.action == "admin_withdraw"))
async def cq_admin_withdraw_participant(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    await update_participant_status(session, p.id, ParticipantStatus.WITHDRAWN)
    await callback.answer("🚫 Участник снят с соревнования.")

    participants = await list_participants(session, callback_data.tid)
    await callback.message.edit_text(
        f"👥 *Участники* — `{len(participants)}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=participant_list_kb(participants, callback_data.tid),
    )
