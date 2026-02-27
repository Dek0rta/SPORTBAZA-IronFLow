"""
Athlete notification service.

After each judged attempt, the athlete receives a styled push notification
directly in their Telegram chat.
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from bot.models.models import Attempt, Participant, AttemptResult, TournamentType

logger = logging.getLogger(__name__)


async def notify_attempt_result(
    bot: Bot,
    attempt: Attempt,
    participant: Participant,
) -> None:
    """
    Send a styled attempt-result notification to the athlete.
    Silently swallows errors (user may have blocked the bot).
    """
    telegram_id: int = participant.user.telegram_id
    lift_types  = participant.tournament.lift_types
    lift_label  = TournamentType.LIFT_LABELS.get(attempt.lift_type, attempt.lift_type)
    lift_emoji  = TournamentType.LIFT_EMOJI.get(attempt.lift_type, "🏋️")

    if attempt.result == AttemptResult.GOOD:
        verdict_line = "✅ *ЗАЧЁТ!*"
    else:
        verdict_line = "❌ *НЕ ЗАЧЁТ*"

    # Compute current best total for notification
    total = participant.total(lift_types)
    total_line = ""
    if total is not None:
        breakdown_parts = []
        for lt in lift_types:
            best = participant.best_lift(lt)
            if best:
                label = TournamentType.LIFT_LABELS.get(lt, lt)
                breakdown_parts.append(f"{label}: `{best:g}`")
        breakdown = " + ".join(breakdown_parts)
        total_line = f"\n💪 *Текущий тоталл:* `{total:g} кг`\n_{breakdown}_"
    elif attempt.result == AttemptResult.BAD:
        total_line = "\n⚠️ _Нет успешных подходов в одной из дисциплин._"

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏟 *Результат подхода*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{lift_emoji} *{lift_label}* — подход №{attempt.attempt_number}\n"
        f"⚖️ Вес: `{attempt.weight_kg:g} кг`\n\n"
        f"{verdict_line}"
        f"{total_line}\n"
    )

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning(
            "Could not notify athlete telegram_id=%d: %s", telegram_id, e
        )


async def notify_registration_confirmed(
    bot: Bot,
    participant: Participant,
) -> None:
    """Notify athlete that admin confirmed their registration."""
    telegram_id = participant.user.telegram_id
    cat = participant.category.display_name if participant.category else "без категории"
    text = (
        f"🎉 *Ваша заявка подтверждена!*\n\n"
        f"🏆 Турнир: *{participant.tournament.name}*\n"
        f"👤 Атлет: {participant.full_name}\n"
        f"⚖️ Вес: `{participant.bodyweight:g} кг`\n"
        f"📂 Категория: {cat}\n\n"
        f"Удачи на помосте! 💪"
    )
    try:
        await bot.send_message(
            chat_id=telegram_id, text=text, parse_mode=ParseMode.MARKDOWN
        )
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning("Could not notify athlete telegram_id=%d: %s", telegram_id, e)


async def notify_announcement(
    bot: Bot,
    participants: list,
    text: str,
    tournament_name: str,
) -> int:
    """
    Broadcast an admin announcement to all non-withdrawn participants.
    Returns the number of successfully delivered messages.
    """
    message = (
        f"📢 *Объявление от организаторов*\n\n"
        f"🏆 {tournament_name}\n\n"
        f"{text}"
    )
    count = 0
    for p in participants:
        try:
            await bot.send_message(
                chat_id=p.user.telegram_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
            )
            count += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
    return count


async def notify_tournament_started(
    bot: Bot,
    participants: list,
    tournament_name: str,
) -> None:
    """Broadcast tournament-start notification to all confirmed participants."""
    text = (
        f"🚀 *Соревнование началось!*\n\n"
        f"🏆 *{tournament_name}*\n\n"
        f"Судьи уже за пультом. Ждите объявления вашей очереди.\n"
        f"Результаты подходов будут приходить сюда в реальном времени. 🏅"
    )
    for p in participants:
        try:
            await bot.send_message(
                chat_id=p.user.telegram_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
