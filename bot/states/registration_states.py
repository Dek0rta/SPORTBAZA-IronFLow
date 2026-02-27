from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """FSM for athlete self-registration flow."""
    choose_tournament = State()   # Select tournament from list
    enter_full_name   = State()   # Text input: full name
    enter_bodyweight  = State()   # Text input: bodyweight in kg
    choose_gender     = State()   # Inline: M / F
    confirm           = State()   # Show summary → confirm or edit
