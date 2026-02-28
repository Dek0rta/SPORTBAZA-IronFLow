"""
Admin formula selector handler.

Allows admin to change the scoring formula (Wilks/DOTS/Glossbrenner/IPF GL/Total)
for any non-draft tournament via a toggle button in the tournament detail panel.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import FormulaSelectCb, TournamentCb, formula_select_kb, tournament_detail_admin_kb
from bot.middlewares import IsAdmin
from bot.models.models import FormulaType
from bot.services import get_tournament, set_tournament_formula

logger = logging.getLogger(__name__)
router = Router(name="admin_formula")
router.callback_query.filter(IsAdmin())


@router.callback_query(FormulaSelectCb.filter(F.action == "toggle"))
async def cq_formula_toggle(
    callback: CallbackQuery,
    callback_data: FormulaSelectCb,
    session: AsyncSession,
) -> None:
    """Show the formula selection keyboard."""
    t = await get_tournament(session, callback_data.tid, load_relations=False)
    if not t:
        await callback.answer("Турнир не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔢 *Выбор формулы для турнира*\n\n"
        f"🏆 {t.name}\n\n"
        f"Текущая формула: *{t.formula_label}*\n\n"
        f"Выберите формулу для подсчёта и ранжирования участников:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=formula_select_kb(t.id, t.scoring_formula),
    )
    await callback.answer()


@router.callback_query(FormulaSelectCb.filter(F.action == "set"))
async def cq_formula_set(
    callback: CallbackQuery,
    callback_data: FormulaSelectCb,
    session: AsyncSession,
) -> None:
    """Apply the selected formula to the tournament."""
    formula = callback_data.formula
    if formula not in FormulaType.ALL:
        await callback.answer("Неизвестная формула.", show_alert=True)
        return

    await set_tournament_formula(session, callback_data.tid, formula)
    t = await get_tournament(session, callback_data.tid)
    if not t:
        await callback.answer("Турнир не найден.", show_alert=True)
        return

    label = FormulaType.LABELS.get(formula, formula)
    await callback.message.edit_text(
        f"✅ *Формула обновлена: {label}*\n\n"
        f"🏆 {t.name}\n\n"
        f"Все результаты и рейтинги теперь будут рассчитываться по формуле *{label}*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )
    await callback.answer(f"✅ {label}")
