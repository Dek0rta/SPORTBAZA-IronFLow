"""
Achievement definitions and computation logic.
Season = calendar year.
"""
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.models.models import Participant, PlatformRecord

DEFINITIONS = [
    # ── Participation ─────────────────────────────────────────────────────────
    {"id": "first_reg",     "name": "Первые шаги",       "icon": "🎯", "rarity": "common",    "desc": "Зарегистрировался на первый турнир"},
    {"id": "debut",         "name": "Дебютант",          "icon": "⚡", "rarity": "common",    "desc": "Завершил первый турнир"},
    {"id": "veteran",       "name": "Ветеран",           "icon": "🔥", "rarity": "rare",      "desc": "Завершил 5 турниров"},
    {"id": "experienced",   "name": "Бывалый",           "icon": "💪", "rarity": "epic",      "desc": "Завершил 10 турниров"},
    {"id": "legend",        "name": "Легенда помоста",   "icon": "👑", "rarity": "legendary", "desc": "Завершил 20 турниров"},
    # ── Seasonal ──────────────────────────────────────────────────────────────
    {"id": "active_season", "name": "Активный сезон",    "icon": "📅", "rarity": "rare",      "desc": "3+ турнира в одном сезоне (год)"},
    {"id": "marathon",      "name": "Марафонец",         "icon": "🗓️", "rarity": "epic",      "desc": "5+ турниров в одном сезоне (год)"},
    # ── Technical ─────────────────────────────────────────────────────────────
    {"id": "clean_win",     "name": "Чистая победа",     "icon": "✅", "rarity": "rare",      "desc": "9/9 попыток удачно в SBD-турнире"},
    {"id": "perfectionist", "name": "Перфекционист",     "icon": "💯", "rarity": "epic",      "desc": "3 турнира с идеальным 9/9"},
    # ── Records ───────────────────────────────────────────────────────────────
    {"id": "record_holder", "name": "Рекордсмен",        "icon": "📊", "rarity": "epic",      "desc": "Установил платформенный рекорд"},
    {"id": "record_book",   "name": "Книга рекордов",    "icon": "🏅", "rarity": "legendary", "desc": "Держит 3+ рекорда платформы"},
    # ── Weight milestones ─────────────────────────────────────────────────────
    {"id": "club_500",      "name": "Клуб 500",          "icon": "🔱", "rarity": "rare",      "desc": "Тотал SBD ≥ 500 кг"},
    {"id": "club_650",      "name": "Клуб 650",          "icon": "⚔️", "rarity": "epic",      "desc": "Тотал SBD ≥ 650 кг"},
    {"id": "titan",         "name": "Мастер тяжести",    "icon": "🌊", "rarity": "legendary", "desc": "Тотал SBD ≥ 800 кг"},
    # ── Formula score ─────────────────────────────────────────────────────────
    {"id": "scientist",     "name": "Учёный помоста",    "icon": "🧬", "rarity": "rare",      "desc": "DOTS ≥ 300 очков"},
    {"id": "elite_dots",    "name": "Элита",             "icon": "🌟", "rarity": "epic",      "desc": "DOTS ≥ 400 очков"},
    {"id": "supreme",       "name": "Надчеловек",        "icon": "🔬", "rarity": "legendary", "desc": "DOTS ≥ 500 очков"},
    # ── Consistency ───────────────────────────────────────────────────────────
    {"id": "punctual",      "name": "Пунктуальный",      "icon": "⏰", "rarity": "common",    "desc": "Прошёл QR-регистрацию на турнире"},
    {"id": "loyal",         "name": "Верность",          "icon": "🛡️", "rarity": "rare",      "desc": "5+ турниров без снятия"},
    {"id": "versatile",     "name": "Многоборец",        "icon": "🎲", "rarity": "rare",      "desc": "Участвовал в 3 разных видах соревнований"},
]


def _dots(bodyweight: float, total: float, gender: str) -> float:
    bw = max(40.0, min(210.0, bodyweight))
    if gender == "M":
        a, b, c, d, e, f = -0.0000010930, 0.0000920904, -0.0027140341, 0.0101818720, -0.0576488983, 4.0475488
    else:
        a, b, c, d, e, f = -0.0000010706, 0.0000938772, -0.0027892793, 0.0101526476, -0.0550588635, 4.3805268
    denom = a*bw**5 + b*bw**4 + c*bw**3 + d*bw**2 + e*bw + f
    return round(500.0 / denom * total, 2) if denom else 0.0


def compute(
    participations: list,  # Participant objects with .attempts and .tournament loaded
    records: list,         # PlatformRecord objects
    withdrawn_count: int,
) -> list[dict]:
    achieved: set[str] = set()

    # ── Participation counts ──────────────────────────────────────────────────
    # "completed" = finished tournament with at least one successful lift
    completed = [
        p for p in participations
        if p.tournament.status == "finished"
        and any(a.result == "good" for a in p.attempts)
    ]

    if participations:
        achieved.add("first_reg")
    if completed:
        achieved.add("debut")
    if len(completed) >= 5:
        achieved.add("veteran")
    if len(completed) >= 10:
        achieved.add("experienced")
    if len(completed) >= 20:
        achieved.add("legend")

    # ── Seasonal ─────────────────────────────────────────────────────────────
    current_year = datetime.now().year
    season_completed = [
        p for p in completed
        if p.tournament.created_at and p.tournament.created_at.year == current_year
    ]
    if len(season_completed) >= 3:
        achieved.add("active_season")
    if len(season_completed) >= 5:
        achieved.add("marathon")

    # ── Technical: perfect lifts ──────────────────────────────────────────────
    clean_count = 0
    for p in completed:
        if p.tournament.tournament_type == "SBD":
            good = sum(1 for a in p.attempts if a.result == "good")
            if good >= 9:
                clean_count += 1
    if clean_count >= 1:
        achieved.add("clean_win")
    if clean_count >= 3:
        achieved.add("perfectionist")

    # ── Records ───────────────────────────────────────────────────────────────
    if records:
        achieved.add("record_holder")
    if len(records) >= 3:
        achieved.add("record_book")

    # ── Weight milestones ─────────────────────────────────────────────────────
    best_sbd = 0.0
    best_dots = 0.0
    for p in completed:
        sbd = p.total(["squat", "bench", "deadlift"])
        if sbd:
            best_sbd = max(best_sbd, sbd)
        any_total = sbd or p.total(["bench", "deadlift"]) or p.total(["bench"]) or p.total(["deadlift"]) or 0
        if any_total and p.bodyweight and p.gender:
            best_dots = max(best_dots, _dots(p.bodyweight, any_total, p.gender))

    if best_sbd >= 500:  achieved.add("club_500")
    if best_sbd >= 650:  achieved.add("club_650")
    if best_sbd >= 800:  achieved.add("titan")
    if best_dots >= 300: achieved.add("scientist")
    if best_dots >= 400: achieved.add("elite_dots")
    if best_dots >= 500: achieved.add("supreme")

    # ── Consistency ───────────────────────────────────────────────────────────
    if any(p.checked_in for p in participations):
        achieved.add("punctual")
    if withdrawn_count == 0 and len(completed) >= 5:
        achieved.add("loyal")
    types_used = {p.tournament.tournament_type for p in completed}
    if len(types_used) >= 3:
        achieved.add("versatile")

    return [{**d, "unlocked": d["id"] in achieved} for d in DEFINITIONS]
