"""
Global fallback handler — included LAST in the dispatcher.

Catches any callback query that no other router handled.
Prevents infinite Telegram spinners from:
  - Stale keyboards after bot restart (MemoryStorage is wiped on redeploy)
  - Unimplemented callback paths
"""
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards import athlete_main_menu, admin_main_menu

router = Router(name="fallback")


@router.callback_query()
async def cq_fallback(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool = False,
) -> None:
    await callback.answer("⚠️ Кнопка устарела. Начните заново.", show_alert=True)
    await state.clear()
    try:
        kb = admin_main_menu() if is_admin else athlete_main_menu()
        await callback.message.edit_text(
            "🔄 *Сессия сброшена.* Вернитесь в главное меню:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    except Exception:
        pass
