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

from aiogram.types import BufferedInputFile

from bot.keyboards import (
    MainMenuCb, TournamentCb,
    tournament_list_kb, gender_kb, age_category_kb, opening_weight_kb,
    cancel_registration_kb, confirm_registration_kb, athlete_main_menu,
)
from bot.models.models import AgeCategory
from bot.services import (
    list_open_tournaments, get_tournament, get_user, register_participant,
    get_participant, list_participants,
)
from bot.services.qr_service import make_qr_token, generate_qr_buffered
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

    desc_line = f"\n📝 _{t.description}_\n" if t.description else ""
    await callback.message.edit_text(
        f"✅ *{t.name}*\n"
        f"📋 {t.type_label}"
        f"{desc_line}\n"
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
    await state.set_state(RegistrationStates.choose_age_category)

    g_label = "👨 Мужчины" if gender == "M" else "👩 Женщины"
    await callback.message.edit_text(
        f"🚻 Пол: *{g_label}*\n\n"
        f"Выберите *возрастную категорию*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=age_category_kb(gender),
    )
    await callback.answer()


# ── Step 5: age category ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reg_age:"), RegistrationStates.choose_age_category)
async def cq_age_category(callback: CallbackQuery, state: FSMContext) -> None:
    age_cat = callback.data.split(":")[1]
    data = await state.get_data()
    gender = data.get("gender", "M")
    labels = AgeCategory.LABELS_F if gender == "F" else AgeCategory.LABELS_M
    age_label = labels.get(age_cat, age_cat)
    await state.update_data(age_category=age_cat)
    await state.set_state(RegistrationStates.enter_opening_weight)
    await callback.message.edit_text(
        f"🏅 Возрастная категория: *{age_label}*\n\n"
        f"Введите ваш *первый заявочный вес* (кг, например: `120`):\n"
        f"_Это начальный вес для первой попытки на соревновании._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=opening_weight_kb(),
    )
    await callback.answer()


# ── Step 5.1: text fallback during age-category step ─────────────────────────

@router.message(RegistrationStates.choose_age_category)
async def msg_age_category_hint(message: Message, state: FSMContext) -> None:
    """Catch accidental text input during the age-category selection step."""
    data = await state.get_data()
    gender = data.get("gender", "M")
    await message.answer(
        "👆 Пожалуйста, выберите возрастную категорию, нажав на одну из кнопок:",
        reply_markup=age_category_kb(gender),
    )


# ── Step 5.5: opening weight ──────────────────────────────────────────────────

async def _show_confirm(message_or_callback, state: FSMContext, edit: bool = False) -> None:
    """Render the confirmation screen. Works for both Message and CallbackQuery."""
    data = await state.get_data()
    gender = data.get("gender", "M")
    g_label = "👨 Мужчина" if gender == "M" else "👩 Женщина"
    labels = AgeCategory.LABELS_F if gender == "F" else AgeCategory.LABELS_M
    age_label = labels.get(data.get("age_category", ""), data.get("age_category", ""))
    ow = data.get("opening_weight")
    ow_line = f"🏋️ Первый вес: `{ow:g} кг`\n" if ow else ""

    text = (
        f"📝 *Проверьте данные заявки:*\n\n"
        f"🏆 Турнир: *{data['tournament_name']}*\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"⚖️ Собственный вес: `{data['bodyweight']:g} кг`\n"
        f"🚻 Пол: {g_label}\n"
        f"🏅 Возрастная категория: {age_label}\n"
        f"{ow_line}\n"
        f"_Весовая категория будет определена автоматически._"
    )
    markup = confirm_registration_kb()
    if edit:
        await message_or_callback.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        await message_or_callback.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


@router.message(RegistrationStates.enter_opening_weight)
async def msg_opening_weight(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".") if message.text else ""
    try:
        ow = float(raw)
        if not (0 < ow < 1000):
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ Введите корректный вес (кг), например `120`:",
            reply_markup=opening_weight_kb(),
        )
        return

    await state.update_data(opening_weight=ow)
    await state.set_state(RegistrationStates.confirm)
    await _show_confirm(message, state, edit=False)


@router.callback_query(F.data == "reg_skip_opening_weight", RegistrationStates.enter_opening_weight)
async def cq_skip_opening_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(opening_weight=None)
    await state.set_state(RegistrationStates.confirm)
    await _show_confirm(callback.message, state, edit=True)
    await callback.answer()


# ── Step 6: confirm ───────────────────────────────────────────────────────────

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

    # Generate QR token before registering
    qr_token = make_qr_token()

    participant, error = await register_participant(
        session,
        tournament_id=data["tournament_id"],
        user_id=user.id,
        full_name=data["full_name"],
        bodyweight=data["bodyweight"],
        gender=data["gender"],
        age_category=data.get("age_category"),
        qr_token=qr_token,
        opening_weight=data.get("opening_weight"),
    )

    if error:
        await callback.answer(error, show_alert=True)
        await state.clear()
        return

    await state.clear()

    # Re-fetch with all relationships loaded — the freshly-created participant
    # has lazy relationships that cannot be accessed in async context.
    participant = await get_participant(session, participant.id)

    cat = participant.category.display_name if participant.category else "будет назначена"
    p_labels = AgeCategory.LABELS_F if participant.gender == "F" else AgeCategory.LABELS_M
    age_label = p_labels.get(participant.age_category, "") if participant.age_category else ""
    ow_line = f"🏋️ Первый вес: `{participant.opening_weight:g} кг`\n" if participant.opening_weight else ""
    text = (
        f"🎉 *Вы успешно зарегистрированы!*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *{data['tournament_name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {participant.full_name}\n"
        f"⚖️ Вес: `{participant.bodyweight:g} кг`\n"
        f"🏅 Возрастная категория: {age_label}\n"
        f"{ow_line}"
        f"📂 Весовая категория: {cat}\n"
        f"📌 Статус: ⚪️ Ожидание подтверждения\n\n"
        f"Вы получите уведомление, когда заявка будет подтверждена. 🔔\n\n"
        f"📷 *Ваш QR-билет отправлен ниже* — предъявите его на check-in."
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=athlete_main_menu()
    )
    await callback.answer("✅ Заявка принята!")

    # Send QR ticket as a separate photo message
    try:
        qr_buf = generate_qr_buffered(participant.qr_token or qr_token)
        qr_file = BufferedInputFile(qr_buf.read(), filename="ticket.png")
        await callback.message.answer_photo(
            photo=qr_file,
            caption=(
                f"🎫 *QR-билет*\n"
                f"👤 {participant.full_name}\n"
                f"🏆 {data['tournament_name']}\n\n"
                f"_Предъявите этот код организаторам при регистрации явки._"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.warning("Failed to send QR ticket: %s", exc)


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
