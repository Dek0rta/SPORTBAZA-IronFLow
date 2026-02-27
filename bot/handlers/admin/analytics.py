"""
Admin analytics handler — Academic Impact Report.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelCb, AnalyticsCb, TournamentCb
from bot.middlewares import IsAdmin
from bot.services import list_tournaments, get_tournament, list_participants
from bot.services.analytics_service import build_analytics_report, format_report_text

logger = logging.getLogger(__name__)
router = Router(name="admin_analytics")
router.callback_query.filter(IsAdmin())


@router.callback_query(AdminPanelCb.filter(F.action == "analytics"))
async def cq_analytics_entry(
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
            callback_data=AnalyticsCb(action="report", tid=t.id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="back").pack()
    ))
    await callback.message.edit_text(
        "📊 *Аналитика*\n\nВыберите турнир:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(AnalyticsCb.filter(F.action == "report"))
async def cq_analytics_report(
    callback: CallbackQuery,
    callback_data: AnalyticsCb,
    session: AsyncSession,
) -> None:
    t            = await get_tournament(session, callback_data.tid, load_relations=False)
    participants = await list_participants(session, callback_data.tid, include_withdrawn=False)

    report = build_analytics_report(t.name, t.tournament_type, participants)
    text   = format_report_text(report)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="analytics").pack()
    ))
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()
