from aiogram.fsm.state import State, StatesGroup


class AdminTournamentStates(StatesGroup):
    """FSM for tournament creation wizard."""
    enter_name         = State()  # Tournament name
    choose_type        = State()  # SBD / BP / DL / PP
    choose_categories  = State()  # Multi-select weight categories
    confirm            = State()  # Review + save


class AdminScoringStates(StatesGroup):
    """FSM for live scoring panel."""
    enter_weight = State()   # Admin types attempt weight after clicking ⚖️
