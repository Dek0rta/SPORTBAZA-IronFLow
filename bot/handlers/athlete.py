"""
Athlete personal cabinet: my registrations, profile card, withdraw.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    MainMenuCb, ParticipantCb,
    my_registrations_kb, participant_profile_kb, withdraw_confirm_kb,
    athlete_main_menu,
)
from bot.models.models import TournamentStatus, ParticipantStatus, FormulaType
from bot.services import get_user, get_athlete_registrations, get_participant, update_participant_status
from bot.services.formula_service import get_full_performance_deltas, world_percentile

logger = logging.getLogger(__name__)
router = Router(name="athlete")


# ── My registrations ──────────────────────────────────────────────────────────

@router.callback_query(MainMenuCb.filter(F.action == "my_registrations"))
async def cq_my_registrations(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден. Введите /start", show_alert=True)
        return

    registrations = await get_athlete_registrations(session, user.id)
    active = [r for r in registrations if r.status != ParticipantStatus.WITHDRAWN]

    if not active:
        await callback.message.edit_text(
            "📋 *Мои заявки*\n\n_У вас нет активных заявок._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=athlete_main_menu(),
        )
    else:
        await callback.message.edit_text(
            "📋 *Мои заявки*\n\nВыберите турнир:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=my_registrations_kb(active),
        )
    await callback.answer()


# ── Participant profile card ──────────────────────────────────────────────────

@router.callback_query(ParticipantCb.filter(F.action == "view"))
async def cq_participant_profile(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p or p.user.telegram_id != callback.from_user.id:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    # Performance delta (shown only for finished tournaments)
    delta_lines: list[str] = []
    if p.tournament.status == TournamentStatus.FINISHED:
        try:
            delta_lines = await get_full_performance_deltas(session, p.user.id)
        except Exception:
            pass

    # World percentile estimate (for finished tournaments with a valid total)
    percentile_line = ""
    if p.tournament.status == TournamentStatus.FINISHED and p.category:
        lift_types = p.tournament.lift_types
        total = p.total(lift_types)
        if total is not None:
            pct = world_percentile(p.gender, p.category.name, total)
            if pct is not None:
                percentile_line = f"\n🌍 *Мировой рейтинг:* Вы сильнее, чем *{pct}%* атлетов в вашей категории"

    text = _build_profile_card(p, delta_lines, percentile_line)
    can_withdraw = p.tournament.status in (
        TournamentStatus.REGISTRATION,
        TournamentStatus.DRAFT,
    ) and p.status != ParticipantStatus.WITHDRAWN

    # Athlete can declare weights during registration OR active phase (unjudged attempts)
    can_declare = p.tournament.status in (
        TournamentStatus.REGISTRATION,
        TournamentStatus.ACTIVE,
    ) and p.status != ParticipantStatus.WITHDRAWN

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=participant_profile_kb(
            p.id,
            can_withdraw=can_withdraw,
            can_declare_weights=can_declare,
        ),
    )
    await callback.answer()


def _build_profile_card(p, delta_lines: list = None, percentile_line: str = "") -> str:
    """Render a rich athlete profile summary card."""
    cat       = p.category.display_name if p.category else "не назначена"
    lot       = f"`#{p.lot_number}`" if p.lot_number else "_не назначен_"
    t_type    = p.tournament.type_label
    t_status  = p.tournament.status_emoji
    lift_types = p.tournament.lift_types

    lines = [
        f"━━━━━━━━━━━━━━━━━━",
        f"👤 *{p.full_name}*",
        f"━━━━━━━━━━━━━━━━━━",
        f"",
        f"🏆 Турнир: *{p.tournament.name}*",
        f"📌 Тип: {t_type}  {t_status}",
        f"📂 Категория: {cat}",
        f"⚖️ Вес: `{p.bodyweight:g} кг`",
        f"🎲 Жребий: {lot}",
        f"📋 Статус заявки: {p.status_emoji} {_status_label(p.status)}",
    ]

    # Show attempts if competition is active
    if p.attempts and p.tournament.status in (TournamentStatus.ACTIVE, TournamentStatus.FINISHED):
        lines += ["", "━━━ Подходы ━━━"]
        from bot.models.models import TournamentType
        for lt in lift_types:
            lbl  = TournamentType.LIFT_LABELS.get(lt, lt)
            best = p.best_lift(lt)
            lt_attempts = sorted(
                [a for a in p.attempts if a.lift_type == lt],
                key=lambda a: a.attempt_number,
            )
            attempt_strs = [
                f"{a.result_emoji}`{a.display_weight}`" for a in lt_attempts
            ]
            best_str = f"*{best:g} кг*" if best else "_бомб-аут_"
            lines.append(f"{lbl}: {' '.join(attempt_strs)}  → {best_str}")

        total = p.total(lift_types)
        if total is not None:
            lines.append(f"\n💪 *Тоталл: `{total:g} кг`*")

    if percentile_line:
        lines.append(percentile_line)

    if delta_lines:
        lines += ["", "━━━ Прогресс ━━━"] + delta_lines

    return "\n".join(lines)


def _status_label(status: str) -> str:
    return {
        ParticipantStatus.REGISTERED: "Ожидание подтверждения",
        ParticipantStatus.CONFIRMED:  "Подтверждена",
        ParticipantStatus.WITHDRAWN:  "Отменена",
    }.get(status, status)


# ── Withdraw ──────────────────────────────────────────────────────────────────

@router.callback_query(ParticipantCb.filter(F.action == "withdraw"))
async def cq_withdraw_prompt(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p or p.user.telegram_id != callback.from_user.id:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        f"❓ Вы уверены, что хотите *отменить участие* в турнире\n"
        f"*{p.tournament.name}*?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=withdraw_confirm_kb(p.id),
    )
    await callback.answer()


@router.callback_query(ParticipantCb.filter(F.action == "withdraw_confirm"))
async def cq_withdraw_confirm(
    callback: CallbackQuery,
    callback_data: ParticipantCb,
    session: AsyncSession,
) -> None:
    p = await get_participant(session, callback_data.pid)
    if not p or p.user.telegram_id != callback.from_user.id:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    await update_participant_status(session, p.id, ParticipantStatus.WITHDRAWN)
    await callback.message.edit_text(
        f"🚫 *Участие в турнире отменено.*\n\n"
        f"Вы всегда можете зарегистрироваться снова, пока регистрация открыта.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=athlete_main_menu(),
    )
    await callback.answer("Заявка отменена.")


# ── Public tournament list ────────────────────────────────────────────────────

@router.callback_query(MainMenuCb.filter(F.action == "tournaments_public"))
async def cq_public_tournaments(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    from bot.services import list_tournaments
    from bot.models.models import TournamentType

    tournaments = await list_tournaments(session)
    if not tournaments:
        await callback.message.edit_text(
            "🏆 *Турниры*\n\n_Нет доступных турниров._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=athlete_main_menu(),
        )
        await callback.answer()
        return

    lines = ["🏆 *Актуальные турниры:*\n"]
    for t in tournaments:
        lines.append(
            f"{t.status_emoji} *{t.name}*\n"
            f"   ├ Тип: {t.type_label}\n"
            f"   └ Статус: {_tournament_status_label(t.status)}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=athlete_main_menu(),
    )
    await callback.answer()


def _tournament_status_label(status: str) -> str:
    return {
        "draft":        "📝 Настройка",
        "registration": "📋 Регистрация открыта",
        "active":       "🔴 Идут соревнования",
        "finished":     "🏁 Завершён",
    }.get(status, status)
