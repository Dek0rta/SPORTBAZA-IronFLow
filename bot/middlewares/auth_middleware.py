"""
Admin authorization middleware.

Attaches `is_admin: bool` to handler data for all updates.
The AdminOnly filter (below) can be used as a router-level filter.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.config import settings


class AdminMiddleware(BaseMiddleware):
    """
    Injects `is_admin` flag into data dict.
    Applied globally — individual routers restrict access via filters.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        data["is_admin"] = bool(user and user.id in settings.admin_ids_list)
        return await handler(event, data)


# ── Reusable filter ──────────────────────────────────────────────────────────

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery


class IsAdmin(BaseFilter):
    """Use on individual routers/handlers to restrict access to admins."""

    async def __call__(self, event: Message | CallbackQuery, is_admin: bool = False) -> bool:
        if not is_admin:
            if isinstance(event, Message):
                await event.answer("⛔️ Доступ запрещён.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔️ Доступ запрещён.", show_alert=True)
        return is_admin
