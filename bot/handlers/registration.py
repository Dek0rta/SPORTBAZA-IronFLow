"""
Athlete self-registration FSM handler.

Flow:
  /start → choose tournament → enter full name → enter bodyweight
         → choose gender → confirm → saved ✅
"""
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    MainMenuCb, TournamentCb,
    tournament_list_kb, gender_kb, cancel_registration_kb,
    confirm_registration_kb, athlete_main_menu,
)
from bot.services import (
    list_open_tournaments, get_tournament, get_user, register_participant,
    get_participant,
)
from bot.states import RegistrationStates

logger = logging.getLogger(__name__)
router = Router(name="registration")


# ── Entry: "Register" button ──────────────────────────────────────────────────

@router.callback_query(MainMenuCb.filter(F.action == "register"))
async def cq_start_registration(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    tournaments = await list_open_tournaments(session)
    if not tournaments:
        await callback.answer("Нет открытых турниров.", show_alert=True)
        return

    await state.set_state(RegistrationStates.choose_tournament)
    await callback.message.edit_text(
        "📋 *Выберите турнир для регистрации:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tournament_list_kb(tournaments),
    )
    await callback.answer()


# ── Step 1: tournament chosen ─────────────────────────────────────────────────

@router.callback_query(
    TournamentCb.filter(F.action == "register_select"),
    RegistrationStates.choose_tournament,
)
async def cq_tournament_selected(
    callback: CallbackQuery,
    callback_data: TournamentCb,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    t = await get_tournament(session, callback_data.tid, load_relations=False)
    if not t:
        await callback.answer("Турнир не найден.", show_alert=True)
        return

    await state.update_data(tournament_id=t.id, tournament_name=t.name)
    await state.set_state(RegistrationStates.enter_full_name)

    await callback.message.edit_text(
        f"✅ *{t.name}*\n\n"
        f"Введите ваше *ФИО* (полностью, например: _Иванов Иван Иванович_):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_registration_kb(),
    )
    await callback.answer()


# ── Step 2: full name ─────────────────────────────────────────────────────────

@router.message(RegistrationStates.enter_full_name)
async def msg_full_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if len(name) < 3:
        await message.answer(
            "⚠️ Имя слишком короткое. Введите ФИО полностью:",
            reply_markup=cancel_registration_kb(),
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(RegistrationStates.enter_bodyweight)
    await message.answer(
        f"👤 *{name}*\n\n"
        f"Введите ваш *собственный вес* в кг (например: `87.5`):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_registration_kb(),
    )


# ── Step 3: bodyweight ────────────────────────────────────────────────────────

@router.message(RegistrationStates.enter_bodyweight)
async def msg_bodyweight(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".") if message.text else ""
    try:
        bw = float(raw)
        if not (20 < bw < 400):
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ Введите корректный вес (кг), например `93.5`:",
            reply_markup=cancel_registration_kb(),
        )
        return

    await state.update_data(bodyweight=bw)
    await state.set_state(RegistrationStates.choose_gender)
    await message.answer(
        f"⚖️ Вес: `{bw:g} кг`\n\nВыберите *пол*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=gender_kb(),
    )


# ── Step 4: gender ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reg_gender:"), RegistrationStates.choose_gender)
async def cq_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    await state.set_state(RegistrationStates.confirm)

    data = await state.get_data()
    g_label = "👨 Мужчина" if gender == "M" else "👩 Женщина"

    text = (
        f"📝 *Проверьте данные заявки:*\n\n"
        f"🏆 Турнир: *{data['tournament_name']}*\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"⚖️ Вес: `{data['bodyweight']:g} кг`\n"
        f"🚻 Пол: {g_label}\n\n"
        f"_Категория будет определена автоматически._"
    )
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_registration_kb(),
    )
    await callback.answer()


# ── Step 5: confirm ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "reg_confirm", RegistrationStates.confirm)
async def cq_confirm_registration(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    tg   = callback.from_user

    user = await get_user(session, tg.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    participant, error = await register_participant(
        session,
        tournament_id=data["tournament_id"],
        user_id=user.id,
        full_name=data["full_name"],
        bodyweight=data["bodyweight"],
        gender=data["gender"],
    )

    if error:
        await callback.answer(error, show_alert=True)
        await state.clear()
        return

    await state.clear()

    cat = participant.category.display_name if participant.category else "будет назначена"
    text = (
        f"🎉 *Вы успешно зарегистрированы!*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *{data['tournament_name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {participant.full_name}\n"
        f"⚖️ Вес: `{participant.bodyweight:g} кг`\n"
        f"📂 Категория: {cat}\n"
        f"📌 Статус: ⚪️ Ожидание подтверждения\n\n"
        f"Вы получите уведомление, когда заявка будет подтверждена. 🔔"
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=athlete_main_menu()
    )
    await callback.answer("✅ Заявка принята!")


@router.callback_query(F.data == "reg_edit", RegistrationStates.confirm)
async def cq_edit_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to name entry step."""
    await state.set_state(RegistrationStates.enter_full_name)
    data = await state.get_data()
    await callback.message.edit_text(
        f"✏️ Введите *ФИО* заново:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_registration_kb(),
    )
    await callback.answer()
