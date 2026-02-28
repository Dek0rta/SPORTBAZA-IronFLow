"""
Admin QR Check-in scanner.

Workflow:
  1. Admin taps "📷 QR Check-in" → bot enters waiting_token state
  2. Admin scans athlete's QR ticket with their phone camera → gets UUID
  3. Admin pastes the UUID into the bot (or sends it as text)
  4. Bot looks up the participant, shows their details, marks checked_in=True

The UUID is embedded in the QR code generated at registration time.
Admin can use any QR reader app to decode the code, then paste the result here.
"""
import logging
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.keyboards import AdminPanelCb, admin_main_menu
from bot.middlewares import IsAdmin
from bot.models.models import Participant, ParticipantStatus, AgeCategory
from bot.states import AdminQrScanStates

logger = logging.getLogger(__name__)
router = Router(name="admin_qr_scanner")
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())

# UUID4 regex pattern
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


# ── Entry ─────────────────────────────────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "qr_scan"))
async def cq_qr_scan_entry(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(AdminQrScanStates.waiting_token)
    await callback.message.edit_text(
        "📷 *QR Check-in*\n\n"
        "Отсканируйте QR-билет атлета любым приложением.\n\n"
        "Затем скопируйте полученный UUID (например: `a1b2c3d4-...`) "
        "и отправьте его сюда.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


# ── Token input ───────────────────────────────────────────────────────────────

@router.message(AdminQrScanStates.waiting_token)
async def msg_qr_token(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    raw = message.text.strip() if message.text else ""

    # Extract UUID from message (even if extra text is present)
    match = _UUID_RE.search(raw)
    if not match:
        await message.answer(
            "⚠️ UUID не распознан.\n\n"
            "Убедитесь, что отправляете корректный UUID вида:\n"
            "`a1b2c3d4-e5f6-4abc-8def-1234567890ab`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_cancel_kb(),
        )
        return

    token = match.group(0).lower()

    # Look up participant by qr_token
    stmt = (
        select(Participant)
        .where(Participant.qr_token == token)
        .options(
            selectinload(Participant.tournament),
            selectinload(Participant.category),
            selectinload(Participant.user),
        )
    )
    result = await session.execute(stmt)
    participant = result.scalar_one_or_none()

    if not participant:
        await message.answer(
            "❌ *Токен не найден.*\n\n"
            "Убедитесь, что атлет зарегистрирован на этой платформе.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_cancel_kb(),
        )
        return

    await state.clear()

    if participant.checked_in:
        # Already checked in — show info but do not duplicate
        await message.answer(
            f"ℹ️ *Атлет уже зарегистрирован на явку*\n\n"
            f"{_participant_card(participant)}\n\n"
            f"✅ Явка была подтверждена ранее.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main_menu(),
        )
        return

    if participant.status == ParticipantStatus.WITHDRAWN:
        await message.answer(
            f"⚠️ *Атлет снят с соревнования*\n\n"
            f"{_participant_card(participant)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main_menu(),
        )
        return

    # Mark as checked-in
    participant.checked_in = True
    if participant.status == ParticipantStatus.REGISTERED:
        participant.status = ParticipantStatus.CONFIRMED

    await message.answer(
        f"✅ *Явка подтверждена!*\n\n"
        f"{_participant_card(participant)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_menu(),
    )
    logger.info(
        "QR check-in: participant %d (%s) checked in at tournament %d",
        participant.id,
        participant.full_name,
        participant.tournament_id,
    )


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "qr_cancel")
async def cq_qr_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ *QR-сканирование отменено.*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_menu(),
    )
    await callback.answer()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _participant_card(p: Participant) -> str:
    cat   = p.category.display_name if p.category else "без категории"
    age   = AgeCategory.LABELS.get(p.age_category, "") if p.age_category else ""
    lines = [
        f"👤 *{p.full_name}*",
        f"🏆 Турнир: {p.tournament.name}",
        f"⚖️ Вес: `{p.bodyweight:g} кг`",
        f"📂 Категория: {cat}",
    ]
    if age:
        lines.append(f"🏅 Возраст: {age}")
    lines.append(f"📌 Статус: {p.status_emoji} {p.status.capitalize()}")
    return "\n".join(lines)


def _cancel_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="qr_cancel"))
    return builder.as_markup()
