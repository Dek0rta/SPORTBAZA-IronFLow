"""
Admin export handler — Google Sheets export + inline results table.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelCb, TournamentCb, ExportCb, admin_main_menu
from bot.middlewares import IsAdmin
from bot.models.models import TournamentStatus
from bot.services import list_tournaments, get_tournament, list_participants
from bot.services.ranking_service import compute_rankings, format_total_breakdown
from bot.services.sheets_service import export_to_sheets

logger = logging.getLogger(__name__)
router = Router(name="admin_export")
router.callback_query.filter(IsAdmin())


# ── Entry ─────────────────────────────────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "export"))
async def cq_export_entry(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    tournaments = await list_tournaments(session, status=TournamentStatus.FINISHED)
    active      = await list_tournaments(session, status=TournamentStatus.ACTIVE)
    all_t       = tournaments + active

    if not all_t:
        await callback.answer("Нет турниров для экспорта.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for t in all_t:
        builder.row(InlineKeyboardButton(
            text=f"{t.status_emoji} {t.name}",
            callback_data=TournamentCb(action="export", tid=t.id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="back").pack()
    ))
    await callback.message.edit_text(
        "📤 *Экспорт результатов*\n\nВыберите турнир:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(TournamentCb.filter(F.action == "export"))
async def cq_export_tournament(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    t = await get_tournament(session, callback_data.tid)
    if not t:
        await callback.answer("Турнир не найден.", show_alert=True)
        return

    participants = await list_participants(session, callback_data.tid)
    rankings     = compute_rankings(participants, t.tournament_type)

    # ── Inline results summary ────────────────────────────────────────────────
    lines = [f"🏆 *{t.name}* — Результаты\n"]
    for cat_ranking in rankings:
        cat_name = cat_ranking.category.display_name if cat_ranking.category else "Без кат."
        lines.append(f"\n*📂 {cat_name}*")
        lines.append("─────────────────")

        if not cat_ranking.results:
            lines.append("_Нет участников_")
            continue

        for r in cat_ranking.results:
            place_str = f"🥇" if r.place == 1 else (
                         "🥈" if r.place == 2 else (
                         "🥉" if r.place == 3 else f"`{r.place}.`"))
            if r.total is not None:
                total_str = f"`{r.total:g} кг`"
            else:
                total_str = "_бомб-аут_"

            lines.append(
                f"{place_str} {r.participant.full_name} — {total_str}  "
                f"_{r.participant.bodyweight:g} кг_"
            )

    # ── Sheets export button ──────────────────────────────────────────────────
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from bot.config import settings

    builder = InlineKeyboardBuilder()
    if settings.sheets_enabled:
        builder.row(InlineKeyboardButton(
            text="📊 Выгрузить в Google Sheets",
            callback_data=ExportCb(action="sheets", tid=t.id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="export").pack()
    ))

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "sheets"))
async def cq_export_sheets(
    callback: CallbackQuery,
    callback_data: ExportCb,
    session: AsyncSession,
) -> None:
    await callback.answer("⏳ Экспортирую…")
    t            = await get_tournament(session, callback_data.tid)
    participants = await list_participants(session, callback_data.tid)

    try:
        url = await export_to_sheets(t, participants)
    except Exception as e:
        logger.exception("Sheets export failed: %s", e)
        await callback.message.answer(
            f"❌ Ошибка экспорта: `{e}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if url:
        await callback.message.answer(
            f"✅ *Экспорт завершён!*\n\n📊 [Открыть таблицу]({url})",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await callback.message.answer(
            "⚠️ Google Sheets не настроен. Проверьте переменные GOOGLE_CREDENTIALS_JSON и GOOGLE_SPREADSHEET_ID."
        )
