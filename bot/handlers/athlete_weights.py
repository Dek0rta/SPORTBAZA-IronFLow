"""
Athlete weight-declaration handler.

Allows athletes to declare and modify their attempt weights before
(and during) a competition, as long as the attempt hasn't been judged.

Flow:
  Athlete profile → [⚖️ Заявить / изменить веса]
    → Weight declaration panel (grid of all attempt slots)
    → Tap any slot → FSM text input → weight saved → panel refreshed
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.athlete_weights_kb import declare_weights_kb, cancel_weight_input_kb
from bot.keyboards.callbacks import ParticipantCb
from bot.models.models import TournamentStatus, ParticipantStatus, TournamentType
from bot.services import get_participant, set_attempt_weight
from bot.states import AthleteWeightStates

logger = logging.getLogger(__name__)
router = Router(name="athlete_weights")


# ── Open weight-declaration panel ────────────────────────────────────────────

@router.callback_query(F.data.startswith("aweights_panel:"))
async def cq_weights_panel(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await callback.answer()
    await state.clear()

    pid = int(callback.data.split(":")[1])
    p   = await get_participant(session, pid)

    if not p or p.user.telegram_id != callback.from_user.id:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    t          = p.tournament
    lift_types = t.lift_types
    can_edit   = t.status in (TournamentStatus.REGISTRATION, TournamentStatus.ACTIVE) \
                 and p.status != ParticipantStatus.WITHDRAWN

    text = _build_weights_panel_text(p, lift_types)

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=declare_weights_kb(
            attempts=p.attempts,
            lift_types=lift_types,
            participant_id=pid,
            can_edit=can_edit,
        ),
    )


# ── Tap an attempt slot → start FSM ──────────────────────────────────────────

@router.callback_query(F.data.startswith("adeclare:"))
async def cq_declare_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await callback.answer()

    # Format: adeclare:{pid}:{lift_type}:{attempt_number}
    _, pid_s, lift_type, num_s = callback.data.split(":")
    pid = int(pid_s)
    num = int(num_s)

    p = await get_participant(session, pid)
    if not p or p.user.telegram_id != callback.from_user.id:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    # Guard: can't edit judged attempts
    attempt_map = {(a.lift_type, a.attempt_number): a for a in p.attempts}
    existing = attempt_map.get((lift_type, num))
    if existing and existing.is_judged:
        await callback.answer("Этот подход уже судили — изменить нельзя.", show_alert=True)
        return

    await state.set_state(AthleteWeightStates.entering_weight)
    await state.update_data(pid=pid, lift_type=lift_type, attempt_number=num)

    lift_label  = TournamentType.LIFT_LABELS.get(lift_type, lift_type)
    current_str = ""
    if existing and existing.weight_kg:
        current_str = f"\n_Текущий вес: *{existing.weight_kg:g} кг*_"

    await callback.message.edit_text(
        f"⚖️ *Заявка веса*\n\n"
        f"📍 {lift_label} — подход №{num}{current_str}\n\n"
        f"Введите вес в кг (например: `185` или `185.5`):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_weight_input_kb(pid),
    )


# ── Receive weight text ───────────────────────────────────────────────────────

@router.message(AthleteWeightStates.entering_weight)
async def msg_declare_weight(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    raw = message.text.strip().replace(",", ".") if message.text else ""
    try:
        weight = float(raw)
        if not (0 < weight < 1000):
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ Введите корректный вес, например `185` или `185.5`:",
            reply_markup=None,
        )
        return

    data      = await state.get_data()
    pid       = data["pid"]
    lift_type = data["lift_type"]
    num       = data["attempt_number"]
    await state.clear()

    # Verify ownership and editability
    p = await get_participant(session, pid)
    if not p or p.user.telegram_id != message.from_user.id:
        await message.answer("Ошибка: заявка не найдена.")
        return

    attempt_map = {(a.lift_type, a.attempt_number): a for a in p.attempts}
    existing = attempt_map.get((lift_type, num))
    if existing and existing.is_judged:
        await message.answer("⛔️ Этот подход уже судили — изменить нельзя.")
        return

    # Save weight
    await set_attempt_weight(session, pid, lift_type, num, weight)

    # Reload participant to get fresh attempts list
    p = await get_participant(session, pid)

    lift_label = TournamentType.LIFT_LABELS.get(lift_type, lift_type)
    t          = p.tournament
    lift_types = t.lift_types
    can_edit   = t.status in (TournamentStatus.REGISTRATION, TournamentStatus.ACTIVE)

    text = (
        f"✅ *Вес сохранён!*  {lift_label} П{num}: `{weight:g} кг`\n\n"
        + _build_weights_panel_text(p, lift_types)
    )

    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=declare_weights_kb(
            attempts=p.attempts,
            lift_types=lift_types,
            participant_id=pid,
            can_edit=can_edit,
        ),
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_weights_panel_text(participant, lift_types: list) -> str:
    t   = participant.tournament
    cat = participant.category.display_name if participant.category else "б/к"

    attempt_map = {
        (a.lift_type, a.attempt_number): a for a in participant.attempts
    }

    lines = [
        f"⚖️ *Заявленные веса*",
        f"━━━━━━━━━━━━━━━━━━",
        f"👤 {participant.full_name}",
        f"📂 {cat}  •  🏋️ {t.name}",
        f"",
    ]

    for lt in lift_types:
        lbl   = TournamentType.LIFT_LABELS.get(lt, lt)
        emoji = TournamentType.LIFT_EMOJI.get(lt, "🏋️")
        lines.append(f"{emoji} *{lbl}*")
        slots = []
        for num in (1, 2, 3):
            a = attempt_map.get((lt, num))
            if a and a.is_judged:
                icon = "✅" if a.result == "good" else "❌"
                slots.append(f"{icon} П{num}: `{a.weight_kg:g}`")
            elif a and a.weight_kg:
                slots.append(f"⚪️ П{num}: `{a.weight_kg:g}`")
            else:
                slots.append(f"➕ П{num}: _—_")
        lines.append("  " + "   ".join(slots))
        lines.append("")

    if t.status == TournamentStatus.REGISTRATION:
        lines.append("_Вы можете изменить веса до начала соревнования._")
    elif t.status == TournamentStatus.ACTIVE:
        lines.append("_Можно изменить только незасуженные подходы._")

    return "\n".join(lines)
