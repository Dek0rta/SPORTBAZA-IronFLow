"""
REST API routes for the SPORTBAZA WebApp.
Runs as an aiohttp server alongside the Telegram bot.
"""
from __future__ import annotations

import logging
from aiohttp import web
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from bot.models.models import (
    User, Tournament, Participant, PlatformRecord,
    TournamentStatus, TournamentType, ParticipantStatus,
)
from bot.models.base import AsyncSessionFactory
from bot.api.auth import parse_tg_user
from bot.api import achievements as ach_module
from bot.config import settings

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


# ── CORS middleware ───────────────────────────────────────────────────────────

@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return web.Response(status=204, headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Telegram-Init-Data",
        })
    try:
        response = await handler(request)
    except web.HTTPException as exc:
        response = exc
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _init_data(req: web.Request) -> str:
    return req.headers.get("X-Telegram-Init-Data", "")


def _dots(bodyweight: float, total: float, gender: str) -> float:
    bw = max(40.0, min(210.0, bodyweight))
    if gender == "M":
        a, b, c, d, e, f = -0.0000010930, 0.0000920904, -0.0027140341, 0.0101818720, -0.0576488983, 4.0475488
    else:
        a, b, c, d, e, f = -0.0000010706, 0.0000938772, -0.0027892793, 0.0101526476, -0.0550588635, 4.3805268
    denom = a*bw**5 + b*bw**4 + c*bw**3 + d*bw**2 + e*bw + f
    return round(500.0 / denom * total, 2) if denom else 0.0


def _mmr_tier(participations: list, records: list) -> tuple[int, str, str]:
    """Returns (mmr, rank_label, tier_key)."""
    dots_bonus   = 0
    for p in participations:
        lt = TournamentType.LIFTS.get(p.tournament.tournament_type, [])
        total = p.total(lt) or 0
        if total and p.bodyweight and p.gender:
            dots_bonus = max(dots_bonus, int(_dots(p.bodyweight, total, p.gender) * 2.5))

    mmr = (500
           + len(participations) * 25
           + min(len(records) * 100, 500)
           + dots_bonus)

    TIERS = [
        (650,  "Iron III",   "iron"),
        (800,  "Iron II",    "iron"),
        (950,  "Iron I",     "iron"),
        (1100, "Bronze III", "bronze"),
        (1250, "Bronze II",  "bronze"),
        (1400, "Bronze I",   "bronze"),
        (1550, "Silver III", "silver"),
        (1700, "Silver II",  "silver"),
        (1850, "Silver I",   "silver"),
        (2000, "Gold III",   "gold"),
        (2150, "Gold II",    "gold"),
        (2300, "Gold I",     "gold"),
    ]
    for threshold, label, tier in TIERS:
        if mmr < threshold:
            return mmr, label, tier
    return mmr, "Elite", "elite"


THRESHOLDS = [0, 650, 800, 950, 1100, 1250, 1400, 1550, 1700, 1850, 2000, 2150, 2300, 9999]


def _mmr_bracket(mmr: int) -> tuple[int, int]:
    for i in range(len(THRESHOLDS) - 1):
        if THRESHOLDS[i] <= mmr < THRESHOLDS[i + 1]:
            return THRESHOLDS[i], THRESHOLDS[i + 1]
    return 2300, 9999


# ── GET /api/me ───────────────────────────────────────────────────────────────

@routes.get("/api/me")
async def get_me(req: web.Request):
    user_data = parse_tg_user(_init_data(req))
    tg_id = user_data.get("id", 0) if user_data else 0
    return web.json_response({
        "telegram_id": tg_id,
        "first_name":  user_data.get("first_name", "") if user_data else "",
        "last_name":   user_data.get("last_name")      if user_data else None,
        "username":    user_data.get("username")       if user_data else None,
        "is_admin":    tg_id in settings.admin_ids_list,
        "authenticated": user_data is not None,
    })


# ── GET /api/tournaments ──────────────────────────────────────────────────────

@routes.get("/api/tournaments")
async def get_tournaments(req: web.Request):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tournament).order_by(Tournament.created_at.desc())
        )
        tournaments = result.scalars().all()

        counts_result = await session.execute(
            select(Participant.tournament_id, func.count(Participant.id).label("cnt"))
            .where(Participant.status != ParticipantStatus.WITHDRAWN)
            .group_by(Participant.tournament_id)
        )
        counts = {row.tournament_id: row.cnt for row in counts_result}

    return web.json_response([{
        "id":                t.id,
        "name":              t.name,
        "status":            t.status,
        "status_emoji":      t.status_emoji,
        "tournament_type":   t.tournament_type,
        "type_label":        t.type_label,
        "description":       t.description,
        "formula":           t.scoring_formula,
        "formula_label":     t.formula_label,
        "created_at":        t.created_at.isoformat() if t.created_at else None,
        "tournament_date":   t.tournament_date,
        "participants_count": counts.get(t.id, 0),
    } for t in tournaments])


# ── DELETE /api/tournaments/{id} ─────────────────────────────────────────────

@routes.delete("/api/tournaments/{id}")
async def delete_tournament(req: web.Request):
    user_data = parse_tg_user(_init_data(req))
    if not user_data or user_data.get("id") not in settings.admin_ids_list:
        raise web.HTTPForbidden()

    tid = int(req.match_info["id"])
    async with AsyncSessionFactory() as session:
        t = await session.get(Tournament, tid)
        if not t:
            raise web.HTTPNotFound()
        if t.status != TournamentStatus.FINISHED:
            raise web.HTTPBadRequest(reason="Only finished tournaments can be deleted")
        await session.delete(t)
        await session.commit()

    return web.json_response({"ok": True})


# ── GET /api/leaderboard ──────────────────────────────────────────────────────

@routes.get("/api/leaderboard")
async def get_leaderboard(req: web.Request):
    async with AsyncSessionFactory() as session:
        # Users who competed in at least one finished tournament
        users_result = await session.execute(
            select(User)
            .join(Participant, Participant.user_id == User.id)
            .join(Tournament,  Tournament.id == Participant.tournament_id)
            .where(Tournament.status == TournamentStatus.FINISHED)
            .distinct()
        )
        users = users_result.scalars().all()

        board = []
        for user in users:
            p_result = await session.execute(
                select(Participant)
                .join(Tournament)
                .where(
                    Participant.user_id  == user.id,
                    Tournament.status    == TournamentStatus.FINISHED,
                    Participant.status   != ParticipantStatus.WITHDRAWN,
                )
                .options(selectinload(Participant.attempts), selectinload(Participant.tournament))
            )
            parts = p_result.scalars().all()

            rec_result = await session.execute(
                select(PlatformRecord).where(
                    PlatformRecord.participant_id.in_([p.id for p in parts])
                ) if parts else select(PlatformRecord).where(False)
            )
            recs = rec_result.scalars().all()

            mmr, rank, tier = _mmr_tier(parts, recs)
            board.append({
                "user_id":    user.id,
                "telegram_id": user.telegram_id,
                "first_name": user.first_name,
                "last_name":  user.last_name,
                "username":   user.username,
                "mmr":        mmr,
                "rank":       rank,
                "tier":       tier,
                "tournaments_count": len(parts),
            })

    board.sort(key=lambda x: x["mmr"], reverse=True)
    return web.json_response(board)


# ── GET /api/profile ──────────────────────────────────────────────────────────

_DEFAULT_PROFILE = {
    "mmr": 500, "rank": "Iron III", "tier": "iron",
    "mmr_start": 0, "mmr_next": 650,
    "wins": 0, "losses": 0, "tournaments": 0,
}


@routes.get("/api/profile")
async def get_profile(req: web.Request):
    user_data = parse_tg_user(_init_data(req))
    if not user_data:
        return web.json_response({
            **_DEFAULT_PROFILE,
            "achievements": ach_module.compute([], [], 0),
        })

    tg_id = user_data["id"]

    async with AsyncSessionFactory() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return web.json_response({
                **_DEFAULT_PROFILE,
                "achievements": ach_module.compute([], [], 0),
            })

        # Finished participations — used for MMR, wins/losses, records
        p_result = await session.execute(
            select(Participant)
            .join(Tournament)
            .where(
                Participant.user_id == user.id,
                Tournament.status   == TournamentStatus.FINISHED,
                Participant.status  != ParticipantStatus.WITHDRAWN,
            )
            .options(
                selectinload(Participant.attempts),
                selectinload(Participant.tournament),
            )
        )
        parts = p_result.scalars().all()

        # All non-withdrawn participations — needed for first_reg, punctual, etc.
        all_parts_result = await session.execute(
            select(Participant)
            .join(Tournament)
            .where(
                Participant.user_id == user.id,
                Participant.status  != ParticipantStatus.WITHDRAWN,
            )
            .options(
                selectinload(Participant.attempts),
                selectinload(Participant.tournament),
            )
        )
        all_parts = all_parts_result.scalars().all()

        rec_result = await session.execute(
            select(PlatformRecord).where(
                PlatformRecord.participant_id.in_([p.id for p in parts])
            ) if parts else select(PlatformRecord).where(False)
        )
        recs = rec_result.scalars().all()

        # Withdrawal count
        wd_result = await session.execute(
            select(func.count(Participant.id)).where(
                Participant.user_id == user.id,
                Participant.status  == ParticipantStatus.WITHDRAWN,
            )
        )
        wd_count = wd_result.scalar() or 0

        mmr, rank, tier = _mmr_tier(parts, recs)
        mmr_start, mmr_next = _mmr_bracket(mmr)

        wins = sum(
            1 for p in parts
            if p.total(TournamentType.LIFTS.get(p.tournament.tournament_type, [])) is not None
        )
        losses = len(parts) - wins

        return web.json_response({
            "mmr":          mmr,
            "rank":         rank,
            "tier":         tier,
            "mmr_start":    mmr_start,
            "mmr_next":     mmr_next,
            "wins":         wins,
            "losses":       losses,
            "tournaments":  len(parts),
            "achievements": ach_module.compute(all_parts, recs, wd_count),
        })


# ── GET /api/my-registrations ─────────────────────────────────────────────────

@routes.get("/api/my-registrations")
async def get_my_registrations(req: web.Request):
    user_data = parse_tg_user(_init_data(req))
    if not user_data:
        return web.json_response([])

    tg_id = user_data["id"]

    async with AsyncSessionFactory() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return web.json_response([])

        p_result = await session.execute(
            select(Participant)
            .join(Tournament)
            .where(
                Participant.user_id == user.id,
                Tournament.status.in_([
                    TournamentStatus.REGISTRATION,
                    TournamentStatus.ACTIVE,
                    TournamentStatus.FINISHED,
                ]),
                Participant.status != ParticipantStatus.WITHDRAWN,
            )
            .options(
                selectinload(Participant.tournament),
                selectinload(Participant.category),
            )
            .order_by(Tournament.created_at.desc())
        )
        parts = p_result.scalars().all()

    return web.json_response([{
        "id":                  p.id,
        "tournament_id":       p.tournament_id,
        "name":                p.tournament.name,
        "tournament_status":   p.tournament.status,
        "tournament_type":     p.tournament.tournament_type,
        "discipline":          p.tournament.type_label,
        "weight_class":        p.category.display_name if p.category else "—",
        "registration_status": p.status,
        "qr_token":            p.qr_token,
        "checked_in":          p.checked_in,
        "full_name":           p.full_name,
        "description":         p.tournament.description,
    } for p in parts])
