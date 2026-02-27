"""
Live scoring panel — the digital judges' desk.

UX flow:
  Admin panel → "Live-Судейство" → choose tournament
    → participant list → athlete card with attempt buttons
    → tap ⚖️ to set weight (FSM text input) or ✅/❌ to judge

After judging each attempt:
  1. Keyboard updates immediately (visual feedback)
  2. Athlete receives push notification with result + current total
"""
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    AdminPanelCb, ParticipantCb, AttemptCb, ScoringNavCb,
    scoring_participant_list_kb, scoring_panel_kb, cancel_input_kb,
)
from bot.middlewares import IsAdmin
from bot.models.models import TournamentStatus
from bot.services import (
    list_tournaments, list_participants, get_participant, get_tournament,
    set_attempt_weight, judge_attempt, cancel_attempt_result,
)
from bot.services.notification_service import notify_attempt_result
from bot.states import AdminScoringStates

logger = logging.getLogger(__name__)
router = Router(name="admin_scoring")
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())


# ── Entry: choose active tournament ──────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "scoring"))
async def cq_scoring_entry(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    tournaments = await list_tournaments(session, status=TournamentStatus.ACTIVE)
    if not tournaments:
        await callback.answer("Нет активных соревнований.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for t in tournaments:
        builder.row(InlineKeyboardButton(
            text=f"⚡ {t.name}",
            callback_data=ParticipantCb(action="select_scoring", tid=t.id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", callback_data=AdminPanelCb(action="back").pack()
    ))
    await callback.message.edit_text(
        "⚡ *Live-Судейство*\n\nВыберите соревнование:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


# ── Participant list for scoring ──────────────────────────────────────────────

@router.callback_query(ParticipantCb.filter(F.action == "select_scoring"))
async def cq_scoring_participant_list(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    participants = await list_participants(session, callback_data.tid)
    if not participants:
        await callback.answer("Нет участников.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚡ *Судейство* — выберите атлета:\n_({len(participants)} чел.)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=scoring_participant_list_kb(participants, callback_data.tid),
    )
    await callback.answer()


# ── Athlete scoring card ──────────────────────────────────────────────────────

@router.callback_query(ParticipantCb.filter(F.action == "scoring"))
async def cq_scoring_card(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await _show_scoring_card(callback, callback_data.pid, callback_data.tid, session)


async def _show_scoring_card(
    callback: CallbackQuery,
    participant_id: int,
    tournament_id: int,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, participant_id)
    t = await get_tournament(session, tournament_id, load_relations=False)
    if not p or not t:
        await callback.answer("Данные не найдены.", show_alert=True)
        return

    participants = await list_participants(session, tournament_id)
    ids          = [x.id for x in participants]
    idx          = ids.index(participant_id) if participant_id in ids else -1
    prev_pid     = ids[idx - 1] if idx > 0     else None
    next_pid     = ids[idx + 1] if idx < len(ids) - 1 else None

    cat      = p.category.display_name if p.category else "б/к"
    total    = p.total(t.lift_types)
    total_str = f"`{total:g} кг`" if total is not None else "_—_"

    text = (
        f"⚡ *СУДЕЙСТВО*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{p.full_name}*\n"
        f"⚖️ `{p.bodyweight:g} кг`  •  📂 {cat}\n"
        f"🎲 Жребий: `#{p.lot_number or '?'}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Тоталл: {total_str}\n"
    )

    kb = scoring_panel_kb(
        attempts=p.attempts,
        lift_types=t.lift_types,
        participant_id=p.id,
        tournament_id=tournament_id,
        prev_pid=prev_pid,
        next_pid=next_pid,
    )

    try:
        await callback.message.edit_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )
    await callback.answer()


# ── Set attempt weight (FSM) ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("att_new:"))
async def cq_set_weight_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    # Format: att_new:{pid}:{lift_type}:{attempt_number}
    _, pid_s, lift_type, num_s = callback.data.split(":")
    pid = int(pid_s)
    num = int(num_s)

    p = await get_participant(session, pid)
    tid = p.tournament_id if p else 0

    await state.set_state(AdminScoringStates.enter_weight)
    await state.update_data(
        participant_id=pid,
        lift_type=lift_type,
        attempt_number=num,
        tournament_id=tid,
    )

    from bot.models.models import TournamentType
    lift_label = TournamentType.LIFT_LABELS.get(lift_type, lift_type)

    # Extract tournament_id from current keyboard if possible (we'll fetch later)
    await callback.message.edit_text(
        f"⚖️ *Задать вес снаряда*\n\n"
        f"📍 {lift_label} — подход №{num}\n\n"
        f"Введите вес в кг (например: `185.5`):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_input_kb(pid, 0),
    )
    await callback.answer()


@router.message(AdminScoringStates.enter_weight)
async def msg_attempt_weight(
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
            "⚠️ Введите корректный вес (кг), например `205`:",
            reply_markup=None,
        )
        return

    data      = await state.get_data()
    pid       = data["participant_id"]
    lift_type = data["lift_type"]
    num       = data["attempt_number"]

    attempt = await set_attempt_weight(session, pid, lift_type, num, weight)
    await state.clear()

    # Fetch participant + tournament to refresh card
    p = await get_participant(session, pid)
    if not p:
        await message.answer("Ошибка: участник не найден.")
        return

    t = await get_tournament(session, p.tournament_id, load_relations=False)
    participants = await list_participants(session, p.tournament_id)
    ids          = [x.id for x in participants]
    idx          = ids.index(pid) if pid in ids else -1
    prev_pid     = ids[idx - 1] if idx > 0 else None
    next_pid     = ids[idx + 1] if idx < len(ids) - 1 else None

    cat      = p.category.display_name if p.category else "б/к"
    total    = p.total(t.lift_types)
    total_str = f"`{total:g} кг`" if total is not None else "_—_"

    text = (
        f"⚡ *СУДЕЙСТВО*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{p.full_name}*\n"
        f"⚖️ `{p.bodyweight:g} кг`  •  📂 {cat}\n"
        f"🎲 Жребий: `#{p.lot_number or '?'}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Тоталл: {total_str}\n"
    )

    kb = scoring_panel_kb(
        attempts=p.attempts,
        lift_types=t.lift_types,
        participant_id=p.id,
        tournament_id=p.tournament_id,
        prev_pid=prev_pid,
        next_pid=next_pid,
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ── Judge attempt ─────────────────────────────────────────────────────────────

@router.callback_query(AttemptCb.filter(F.action.in_({"good", "bad"})))
async def cq_judge_attempt(
    callback: CallbackQuery,
    callback_data: AttemptCb,
    session: AsyncSession,
) -> None:
    from bot.models.models import AttemptResult
    result  = AttemptResult.GOOD if callback_data.action == "good" else AttemptResult.BAD
    attempt = await judge_attempt(session, callback_data.aid, result)
    if not attempt:
        await callback.answer("Подход не найден.", show_alert=True)
        return

    # Reload participant with fresh attempts
    p = await get_participant(session, callback_data.pid)
    t = await get_tournament(session, p.tournament_id, load_relations=False)

    # Notify athlete asynchronously
    try:
        await notify_attempt_result(callback.bot, attempt, p)
    except Exception as e:
        logger.warning("Notification failed: %s", e)

    # Refresh scoring card
    await _refresh_scoring_card_in_place(callback, p, t, session)


@router.callback_query(AttemptCb.filter(F.action == "cancel_result"))
async def cq_cancel_result(
    callback: CallbackQuery,
    callback_data: AttemptCb,
    session: AsyncSession,
) -> None:
    await cancel_attempt_result(session, callback_data.aid)
    p = await get_participant(session, callback_data.pid)
    t = await get_tournament(session, p.tournament_id, load_relations=False)
    await _refresh_scoring_card_in_place(callback, p, t, session)


# ── Navigation ────────────────────────────────────────────────────────────────

@router.callback_query(ScoringNavCb.filter(F.action.in_({"prev", "next"})))
async def cq_scoring_nav(
    callback: CallbackQuery,
    callback_data: ScoringNavCb,
    session: AsyncSession,
) -> None:
    await _show_scoring_card(callback, callback_data.pid, callback_data.tid, session)


@router.callback_query(ScoringNavCb.filter(F.action == "list"))
async def cq_scoring_back_to_list(
    callback: CallbackQuery,
    callback_data: ScoringNavCb,
    session: AsyncSession,
) -> None:
    participants = await list_participants(session, callback_data.tid)
    await callback.message.edit_text(
        f"⚡ *Судейство* — список атлетов:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=scoring_participant_list_kb(participants, callback_data.tid),
    )
    await callback.answer()


# ── Internal helper ───────────────────────────────────────────────────────────

async def _refresh_scoring_card_in_place(callback, p, t, session) -> None:
    """Update the scoring keyboard inline without full message rewrite."""
    participants = await list_participants(session, p.tournament_id)
    ids          = [x.id for x in participants]
    idx          = ids.index(p.id) if p.id in ids else -1
    prev_pid     = ids[idx - 1] if idx > 0             else None
    next_pid     = ids[idx + 1] if idx < len(ids) - 1  else None

    cat      = p.category.display_name if p.category else "б/к"
    total    = p.total(t.lift_types)
    total_str = f"`{total:g} кг`" if total is not None else "_—_"

    text = (
        f"⚡ *СУДЕЙСТВО*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{p.full_name}*\n"
        f"⚖️ `{p.bodyweight:g} кг`  •  📂 {cat}\n"
        f"🎲 Жребий: `#{p.lot_number or '?'}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Тоталл: {total_str}\n"
    )

    kb = scoring_panel_kb(
        attempts=p.attempts,
        lift_types=t.lift_types,
        participant_id=p.id,
        tournament_id=p.tournament_id,
        prev_pid=prev_pid,
        next_pid=next_pid,
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )
    await callback.answer()
