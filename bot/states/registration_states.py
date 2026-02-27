from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """FSM for athlete self-registration flow."""
    choose_tournament = State()
    enter_full_name   = State()
    enter_bodyweight  = State()
    choose_gender     = State()
    confirm           = State()


class AthleteWeightStates(StatesGroup):
    """FSM for athlete self-declaring attempt weights."""
    entering_weight = State()   # Text input: weight for a specific attempt
