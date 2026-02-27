"""
Admin tournament management: create, open registration, start, finish, delete.
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    AdminPanelCb, TournamentCb, CategoryCb,
    tournament_list_admin_kb, tournament_detail_admin_kb,
    confirm_action_kb, category_setup_kb,
    admin_main_menu, PREDEFINED_CATEGORIES,
)
from bot.middlewares import IsAdmin
from bot.models.models import TournamentType, TournamentStatus
from bot.services import (
    create_tournament, get_tournament, list_tournaments,
    set_tournament_status, delete_tournament, create_categories,
    list_participants,
)
from bot.services.notification_service import notify_tournament_started
from bot.states import AdminTournamentStates

logger = logging.getLogger(__name__)
router = Router(name="admin_tournament")
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())


# ── Tournament list ───────────────────────────────────────────────────────────

@router.callback_query(AdminPanelCb.filter(F.action == "tournaments"))
async def cq_tournament_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    tournaments = await list_tournaments(session)
    text = (
        "🎯 *Управление турнирами*\n\n"
        f"Всего: `{len(tournaments)}`"
    )
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_list_admin_kb(tournaments),
    )
    await callback.answer()


@router.callback_query(TournamentCb.filter(F.action == "list"))
async def cq_tournament_list_back(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    tournaments = await list_tournaments(session)
    await callback.message.edit_text(
        "🎯 *Управление турнирами*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_list_admin_kb(tournaments),
    )
    await callback.answer()


# ── Tournament detail ─────────────────────────────────────────────────────────

@router.callback_query(TournamentCb.filter(F.action == "view"))
async def cq_tournament_view(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    t = await get_tournament(session, callback_data.tid)
    if not t:
        await callback.answer("Турнир не найден.", show_alert=True)
        return

    participants = [p for p in t.participants if p.status != "withdrawn"]
    cats = t.categories

    text = (
        f"{t.status_emoji} *{t.name}*\n\n"
        f"📋 Тип: {t.type_label}\n"
        f"📌 Статус: {_status_label(t.status)}\n"
        f"👥 Участников: `{len(participants)}`\n"
        f"📂 Категорий: `{len(cats)}`\n"
    )
    if cats:
        cat_names = ", ".join(c.display_name for c in cats[:5])
        if len(cats) > 5:
            cat_names += f" и ещё {len(cats) - 5}"
        text += f"   _{cat_names}_\n"

    if t.description:
        text += f"\n📝 {t.description}\n"

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )
    await callback.answer()


# ── Create tournament (FSM) ───────────────────────────────────────────────────

@router.callback_query(TournamentCb.filter(F.action == "create"))
async def cq_create_tournament_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(AdminTournamentStates.enter_name)
    await callback.message.edit_text(
        "➕ *Новый турнир*\n\nВведите *название* турнира:",
        parse_mode=ParseMode.MARKDOWN,
    )
    await callback.answer()


@router.message(AdminTournamentStates.enter_name)
async def msg_tournament_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if len(name) < 3:
        await message.answer("⚠️ Название должно быть не менее 3 символов.")
        return

    await state.update_data(name=name)
    await state.set_state(AdminTournamentStates.choose_type)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for key, label in TournamentType.LABELS.items():
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"trn_type:{key}",
        ))
    await message.answer(
        f"🏷 *{name}*\n\nВыберите *тип турнира*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("trn_type:"), AdminTournamentStates.choose_type)
async def cq_tournament_type(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    t_type = callback.data.split(":")[1]
    await state.update_data(tournament_type=t_type)
    await state.set_state(AdminTournamentStates.choose_categories)

    # Start with all categories selected by default
    selected = set()
    data = await state.get_data()
    await state.update_data(selected_categories=list(selected))

    # Show empty selection by default (admin builds from scratch)
    tid_placeholder = 0
    await callback.message.edit_text(
        f"📂 Выберите *весовые категории* для турнира:\n\n"
        f"_(Нажмите на категорию, чтобы включить/выключить)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=category_setup_kb(tid_placeholder, selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_toggle:"))
async def cq_category_toggle(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    # Answer immediately — prevents infinite spinner regardless of what happens next
    await callback.answer()

    # Guard: state may have been lost after bot restart (MemoryStorage is volatile)
    current_state = await state.get_state()
    if current_state != AdminTournamentStates.choose_categories.state:
        await callback.message.edit_text(
            "⚠️ *Сессия устарела.*\n\nНачните создание турнира заново.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main_menu(),
        )
        return

    # Format: cat_toggle:{tid}:{gender}:{cat_name}
    parts  = callback.data.split(":")
    gender = parts[2]
    name   = parts[3]
    key    = f"{gender}:{name}"

    data     = await state.get_data()
    selected = set(data.get("selected_categories", []))

    if key in selected:
        selected.discard(key)
    else:
        selected.add(key)

    await state.update_data(selected_categories=list(selected))
    await callback.message.edit_reply_markup(
        reply_markup=category_setup_kb(0, selected)
    )


@router.callback_query(CategoryCb.filter(F.action == "confirm"))
async def cq_categories_confirmed(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    # Answer FIRST — Telegram clears the spinner immediately, no infinite loading
    await callback.answer()

    # Guard: state may have been lost after bot restart
    current_state = await state.get_state()
    if current_state != AdminTournamentStates.choose_categories.state:
        await callback.message.edit_text(
            "⚠️ *Сессия устарела.*\n\nНачните создание турнира заново.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main_menu(),
        )
        return

    data     = await state.get_data()
    selected = set(data.get("selected_categories", []))

    if not selected:
        await callback.answer("⚠️ Выберите хотя бы одну категорию!", show_alert=True)
        return

    # Create tournament
    t = await create_tournament(
        session,
        name=data["name"],
        tournament_type=data["tournament_type"],
        created_by=callback.from_user.id,
    )

    # Create categories
    cat_tuples = []
    for key in selected:
        gender, cat_name = key.split(":", 1)
        cat_tuples.append((gender, cat_name))

    await create_categories(session, t.id, cat_tuples)
    await state.clear()

    cat_list = ", ".join(
        f"{'М' if g=='M' else 'Ж'}{n}" for g, n in sorted(cat_tuples)
    )
    await callback.message.edit_text(
        f"✅ *Турнир создан!*\n\n"
        f"🏆 {t.name}\n"
        f"📋 Тип: {t.type_label}\n"
        f"📂 Категорий: {len(cat_tuples)}\n"
        f"   _{cat_list}_\n\n"
        f"Турнир в статусе *«Черновик»*.\n"
        f"Откройте регистрацию, когда будете готовы.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )


# ── Status transitions ────────────────────────────────────────────────────────

@router.callback_query(TournamentCb.filter(F.action == "open_reg"))
async def cq_open_registration(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    await set_tournament_status(session, callback_data.tid, TournamentStatus.REGISTRATION)
    t = await get_tournament(session, callback_data.tid)
    await callback.message.edit_text(
        f"📋 *Регистрация открыта!*\n\n"
        f"Атлеты могут теперь регистрироваться на *{t.name}*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )
    await callback.answer("📋 Регистрация открыта!")


@router.callback_query(TournamentCb.filter(F.action == "start"))
async def cq_start_tournament(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    t            = await get_tournament(session, callback_data.tid)
    participants = await list_participants(session, callback_data.tid)
    if not participants:
        await callback.answer("⚠️ Нет зарегистрированных участников!", show_alert=True)
        return

    await set_tournament_status(session, callback_data.tid, TournamentStatus.ACTIVE)
    t = await get_tournament(session, callback_data.tid)

    # Assign lot numbers
    for i, p in enumerate(participants, start=1):
        p.lot_number = i

    from bot.services.notification_service import notify_tournament_started
    await notify_tournament_started(callback.bot, participants, t.name)

    await callback.message.edit_text(
        f"🚀 *Соревнование началось!*\n\n"
        f"*{t.name}* — статус: 🔴 АКТИВНО\n"
        f"Участников: `{len(participants)}`\n\n"
        f"Все атлеты получили уведомление.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )
    await callback.answer("🚀 Старт!")


@router.callback_query(TournamentCb.filter(F.action == "finish_confirm"))
async def cq_finish_confirm(
    callback: CallbackQuery,
    callback_data: TournamentCb,
) -> None:
    await callback.message.edit_text(
        "🏁 *Завершить турнир?*\n\nРезультаты будут зафиксированы.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_action_kb(
            yes_cb=TournamentCb(action="finish", tid=callback_data.tid).pack(),
            no_cb=TournamentCb(action="view",   tid=callback_data.tid).pack(),
        ),
    )
    await callback.answer()


@router.callback_query(TournamentCb.filter(F.action == "finish"))
async def cq_finish_tournament(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    await set_tournament_status(session, callback_data.tid, TournamentStatus.FINISHED)
    t = await get_tournament(session, callback_data.tid)
    await callback.message.edit_text(
        f"🏆 *Турнир завершён!*\n\n"
        f"*{t.name}* — результаты зафиксированы.\n"
        f"Вы можете экспортировать их в Google Sheets.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_detail_admin_kb(t),
    )
    await callback.answer("🏁 Завершено!")


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(TournamentCb.filter(F.action == "delete_confirm"))
async def cq_delete_confirm(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    t = await get_tournament(session, callback_data.tid, load_relations=False)
    await callback.message.edit_text(
        f"🗑️ Удалить турнир *{t.name}*?\n\n⚠️ Действие необратимо.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_action_kb(
            yes_cb=TournamentCb(action="delete", tid=callback_data.tid).pack(),
            no_cb=TournamentCb(action="view",    tid=callback_data.tid).pack(),
        ),
    )
    await callback.answer()


@router.callback_query(TournamentCb.filter(F.action == "delete"))
async def cq_delete_tournament(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
) -> None:
    await delete_tournament(session, callback_data.tid)
    tournaments = await list_tournaments(session)
    await callback.message.edit_text(
        "🗑️ *Турнир удалён.*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_list_admin_kb(tournaments),
    )
    await callback.answer("Удалено")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _status_label(status: str) -> str:
    return {
        "draft":        "📝 Черновик",
        "registration": "📋 Регистрация",
        "active":       "🔴 Активен",
        "finished":     "🏁 Завершён",
    }.get(status, status)
