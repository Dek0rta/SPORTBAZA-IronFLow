"""
Common handlers: /start, main menu routing.
"""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import MainMenuCb, athlete_main_menu, admin_main_menu
from bot.services import upsert_user

logger = logging.getLogger(__name__)
router = Router(name="common")


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, is_admin: bool) -> None:
    tg = message.from_user
    await upsert_user(
        session,
        telegram_id=tg.id,
        first_name=tg.first_name,
        last_name=tg.last_name,
        username=tg.username,
    )

    if is_admin:
        await _send_admin_welcome(message)
    else:
        await _send_athlete_welcome(message)


async def _send_athlete_welcome(message: Message) -> None:
    name = message.from_user.first_name
    text = (
        f"🏋️ Добро пожаловать в *SPORTBAZA*, {name}!\n\n"
        f"Здесь вы можете:\n"
        f"• 📋 Зарегистрироваться на турнир\n"
        f"• 📊 Следить за своими результатами\n"
        f"• 🔔 Получать мгновенные уведомления о подходах\n\n"
        f"Выберите действие:"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=athlete_main_menu())


async def _send_admin_welcome(message: Message) -> None:
    name = message.from_user.first_name
    text = (
        f"⚡ *Панель администратора* — {name}\n\n"
        f"Управляйте турнирами, судите подходы в реальном времени\n"
        f"и экспортируйте результаты в Google Sheets.\n\n"
        f"Выберите раздел:"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_menu())


# ── Main menu callback ────────────────────────────────────────────────────────

@router.callback_query(MainMenuCb.filter(F.action == "main"))
async def cq_main_menu(callback: CallbackQuery, is_admin: bool, state: FSMContext) -> None:
    await state.clear()
    if is_admin:
        text = "⚡ *Панель администратора*\n\nВыберите раздел:"
        kb   = admin_main_menu()
    else:
        text = "🏋️ *SPORTBAZA* — Панель атлета\n\nВыберите действие:"
        kb   = athlete_main_menu()

    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cq_noop(callback: CallbackQuery) -> None:
    await callback.answer()
