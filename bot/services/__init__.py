from bot.services.tournament_service import (
    upsert_user, get_user,
    create_tournament, get_tournament, list_tournaments,
    list_open_tournaments, set_tournament_status, set_tournament_formula,
    delete_tournament, create_categories, list_categories,
    register_participant, get_participant, list_participants,
    get_athlete_registrations, update_participant_status,
    set_attempt_weight, judge_attempt, cancel_attempt_result,
)
from bot.services.ranking_service import (
    compute_rankings, compute_overall_rankings, compute_division_rankings,
    format_total_breakdown, format_result_with_formula,
)
from bot.services.notification_service import (
    notify_attempt_result, notify_registration_confirmed,
    notify_tournament_started, notify_announcement,
)
from bot.services.sheets_service import export_to_sheets
from bot.services.analytics_service import build_analytics_report, format_report_text
from bot.services.formula_service import (
    calculate_formula, wilks, dots, glossbrenner, ipf_gl,
    get_performance_delta, get_full_performance_deltas, world_percentile,
)
from bot.services.records_service import (
    update_records_after_tournament, get_records,
    get_available_age_categories, get_available_weight_categories, get_record_count,
)
from bot.services.qr_service import make_qr_token, generate_qr_buffered, generate_qr_png

__all__ = [
    # tournament CRUD
    "upsert_user", "get_user",
    "create_tournament", "get_tournament", "list_tournaments",
    "list_open_tournaments", "set_tournament_status", "set_tournament_formula",
    "delete_tournament",
    "create_categories", "list_categories",
    "register_participant", "get_participant", "list_participants",
    "get_athlete_registrations", "update_participant_status",
    "set_attempt_weight", "judge_attempt", "cancel_attempt_result",
    # ranking
    "compute_rankings", "compute_overall_rankings", "compute_division_rankings",
    "format_total_breakdown", "format_result_with_formula",
    # notifications
    "notify_attempt_result", "notify_registration_confirmed",
    "notify_tournament_started", "notify_announcement",
    # sheets
    "export_to_sheets",
    # analytics
    "build_analytics_report", "format_report_text",
    # formula engine
    "calculate_formula", "wilks", "dots", "glossbrenner", "ipf_gl",
    "get_performance_delta", "get_full_performance_deltas", "world_percentile",
    # records vault
    "update_records_after_tournament", "get_records",
    "get_available_age_categories", "get_available_weight_categories", "get_record_count",
    # QR
    "make_qr_token", "generate_qr_buffered", "generate_qr_png",
]
