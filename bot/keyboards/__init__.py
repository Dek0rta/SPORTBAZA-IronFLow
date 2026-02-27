from bot.keyboards.callbacks import (
    MainMenuCb,
    TournamentCb,
    CategoryCb,
    ParticipantCb,
    AttemptCb,
    ScoringNavCb,
    AdminPanelCb,
    AnalyticsCb,
    ExportCb,
)
from bot.keyboards.main_menu import athlete_main_menu, admin_main_menu, back_to_main
from bot.keyboards.registration_kb import (
    tournament_list_kb,
    age_category_kb,
    gender_kb,
    cancel_registration_kb,
    confirm_registration_kb,
    my_registrations_kb,
    participant_profile_kb,
    withdraw_confirm_kb,
)
from bot.keyboards.admin_kb import (
    tournament_list_admin_kb,
    tournament_detail_admin_kb,
    confirm_action_kb,
    category_setup_kb,
    description_input_kb,
    announce_cancel_kb,
    participant_list_kb,
    participant_detail_admin_kb,
    scoring_participant_list_kb,
    PREDEFINED_CATEGORIES,
)
from bot.keyboards.scoring_kb import scoring_panel_kb, cancel_input_kb

__all__ = [
    # callbacks
    "MainMenuCb", "TournamentCb", "CategoryCb", "ParticipantCb",
    "AttemptCb", "ScoringNavCb", "AdminPanelCb", "AnalyticsCb", "ExportCb",
    # main menu
    "athlete_main_menu", "admin_main_menu", "back_to_main",
    # registration
    "tournament_list_kb", "age_category_kb", "gender_kb", "cancel_registration_kb",
    "confirm_registration_kb", "my_registrations_kb",
    "participant_profile_kb", "withdraw_confirm_kb",
    # admin
    "tournament_list_admin_kb", "tournament_detail_admin_kb",
    "confirm_action_kb", "category_setup_kb",
    "description_input_kb", "announce_cancel_kb",
    "participant_list_kb", "participant_detail_admin_kb",
    "scoring_participant_list_kb", "PREDEFINED_CATEGORIES",
    # scoring
    "scoring_panel_kb", "cancel_input_kb",
]
