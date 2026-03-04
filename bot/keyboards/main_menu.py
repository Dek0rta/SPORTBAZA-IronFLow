"""
Main menu keyboards — context-aware (athlete vs. admin, tournament phase).
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import MainMenuCb, AdminPanelCb
from bot.config import settings


def athlete_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ Зарегистрироваться",    callback_data=MainMenuCb(action="register").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои заявки",            callback_data=MainMenuCb(action="my_registrations").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Текущие турниры",       callback_data=MainMenuCb(action="tournaments_public").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🥇 База рекордов",         callback_data=MainMenuCb(action="records").pack()),
    )
    if settings.WEBAPP_URL:
        builder.row(
            InlineKeyboardButton(
                text="📱 IronFlow Трекер",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )
        )
    return builder.as_markup()


def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎯 Управление турнирами",  callback_data=AdminPanelCb(action="tournaments").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Live-Судейство",        callback_data=AdminPanelCb(action="scoring").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Аналитика",             callback_data=AdminPanelCb(action="analytics").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📤 Экспорт в Google Sheets", callback_data=AdminPanelCb(action="export").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Участники",             callback_data=AdminPanelCb(action="participants").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📷 QR Check-in",           callback_data=AdminPanelCb(action="qr_scan").pack()),
    )
    if settings.WEBAPP_URL:
        builder.row(
            InlineKeyboardButton(
                text="📱 IronFlow Трекер",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )
        )
    return builder.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data=MainMenuCb(action="main").pack()))
    return builder.as_markup()
