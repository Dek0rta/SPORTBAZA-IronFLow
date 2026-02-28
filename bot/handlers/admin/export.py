"""
Admin export handler — Google Sheets export + inline results table.
Now includes: formula scores, overall champion, division rankings,
and triggers Records Vault update on tournament finish.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelCb, TournamentCb, ExportCb, admin_main_menu
from bot.middlewares import IsAdmin
from bot.models.models import TournamentStatus, FormulaType
from bot.services import (
    list_tournaments, get_tournament, list_participants,
    compute_rankings, compute_overall_rankings, compute_division_rankings,
    format_result_with_formula,
)
from bot.services.sheets_service import export_to_sheets
from bot.services.records_service import update_records_after_tournament

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
    formula      = t.scoring_formula
    formula_label = FormulaType.LABELS.get(formula, formula)

    # ── Update Records Vault for finished tournaments ─────────────────────────
    if t.status == TournamentStatus.FINISHED:
        try:
            recs = await update_records_after_tournament(session, t.id)
            if recs:
                logger.info("Records Vault: %d new/updated records from tournament %d", recs, t.id)
        except Exception as exc:
            logger.warning("Records vault update failed: %s", exc)

    # ── Overall (absolute) champion ───────────────────────────────────────────
    overall = compute_overall_rankings(participants, t.tournament_type, formula)
    lines   = [f"🏆 *{t.name}* — Итоговый протокол\n🔢 Формула: *{formula_label}*\n"]

    if overall:
        lines.append("*🥇 Абсолютный зачёт (Overall)*")
        lines.append("─────────────────")
        for r in overall[:5]:
            medal = "🥇" if r.place == 1 else ("🥈" if r.place == 2 else ("🥉" if r.place == 3 else f"`{r.place}.`"))
            lines.append(f"{medal} {format_result_with_formula(r, formula)}")
        lines.append("")

    # ── Division + weight-category rankings ───────────────────────────────────
    divisions = compute_division_rankings(participants, t.tournament_type, formula)
    for div in divisions:
        lines.append(f"\n*🏅 {div.age_label}*")
        for cat_ranking in div.sub_rankings:
            cat_name = cat_ranking.category_display
            lines.append(f"\n*📂 {cat_name}*")
            lines.append("─────────────────")
            if not cat_ranking.results:
                lines.append("_Нет участников_")
                continue
            for r in cat_ranking.results:
                place_str = (
                    "🥇" if r.place == 1 else
                    "🥈" if r.place == 2 else
                    "🥉" if r.place == 3 else
                    f"`{r.place}.`" if r.place else "💣"
                )
                result_text = format_result_with_formula(r, formula)
                bw_str = f"_{r.participant.bodyweight:g} кг_"
                lines.append(f"{place_str} {result_text}  {bw_str}")

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

    full_text = "\n".join(lines)
    # Telegram message limit guard
    if len(full_text) > 4000:
        full_text = full_text[:3900] + "\n\n_…протокол обрезан. Используйте экспорт в Google Sheets для полного протокола._"

    await callback.message.edit_text(
        full_text,
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
