"""
Rate-limiting middleware for SPORTBAZA Iron Flow.

Protects the bot against spam / flood attacks by limiting how many
updates a single Telegram user can send within a rolling time window.

Default: 30 requests per 60 seconds per user.
Users who exceed the limit receive a single throttle alert and are
silently ignored for the remainder of the window.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class RateLimitMiddleware(BaseMiddleware):
    """
    Sliding-window rate limiter.

    Parameters
    ----------
    rate   : maximum number of requests allowed per user per window
    period : window size in seconds
    """

    def __init__(self, rate: int = 30, period: float = 60.0) -> None:
        self._rate   = rate
        self._period = period
        # user_id → deque of timestamps (most recent first)
        self._history: Dict[int, Deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        uid = user.id
        now = time.monotonic()
        window = self._history[uid]

        # Evict timestamps outside the current window
        while window and now - window[-1] > self._period:
            window.pop()

        if len(window) >= self._rate:
            # User exceeded rate limit — throttle silently or send one warning
            await self._throttle_response(event, data)
            return None

        window.appendleft(now)
        return await handler(event, data)

    async def _throttle_response(
        self,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        """Send a single throttle alert and acknowledge callbacks to clear spinners."""
        msg = "⏳ Слишком много запросов. Подождите немного и попробуйте снова."

        # Determine the underlying update type
        update = data.get("event_update")
        if update is None:
            return

        if update.callback_query:
            try:
                await update.callback_query.answer(msg, show_alert=True)
            except Exception:
                pass
        elif update.message:
            try:
                await update.message.answer(msg)
            except Exception:
                pass
