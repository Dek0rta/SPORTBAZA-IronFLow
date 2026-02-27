"""
Google Sheets export service.

Exports full competition results to a Google Spreadsheet using
gspread-asyncio 2.0.0 (wraps gspread 6.x) for non-blocking I/O.

Sheet layout
------------
Row 1: Tournament title
Row 2: Export timestamp
Row 3: blank
For each weight category:
    Row N:   Category header (bold, blue)
    Row N+1: Column headers
    Row N+2…: Athlete rows (top-3 highlighted gold/silver/bronze)
    Row M:   blank separator
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from bot.config import settings
from bot.models.models import Tournament, Participant, AttemptResult, TournamentType
from bot.services.ranking_service import compute_rankings, AthleteResult

logger = logging.getLogger(__name__)

# ── Colour palette (RGB 0-1 float for Sheets API) ────────────────────────────
COLOUR = {
    "header_bg":  {"red": 0.176, "green": 0.310, "blue": 0.576},
    "header_fg":  {"red": 1.0,   "green": 1.0,   "blue": 1.0},
    "cat_bg":     {"red": 0.851, "green": 0.882, "blue": 0.953},
    "gold":       {"red": 1.0,   "green": 0.843, "blue": 0.0},
    "silver":     {"red": 0.753, "green": 0.753, "blue": 0.753},
    "bronze":     {"red": 0.804, "green": 0.498, "blue": 0.196},
}

MEDAL_COLOURS = [COLOUR["gold"], COLOUR["silver"], COLOUR["bronze"]]


async def export_to_sheets(
    tournament: Tournament,
    participants: List[Participant],
) -> Optional[str]:
    """
    Build and populate a Google Sheet with competition results.
    Returns the spreadsheet URL on success, None if Sheets is not configured.
    """
    if not settings.sheets_enabled:
        logger.warning("Google Sheets export requested but not configured.")
        return None

    try:
        import gspread_asyncio
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.error("gspread-asyncio or google-auth not installed.")
        return None

    creds_info = settings.google_credentials
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    def _make_credentials():
        return Credentials.from_service_account_info(creds_info, scopes=scopes)

    # gspread-asyncio 2.0.0: AsyncioGspreadClientManager API unchanged
    agcm = gspread_asyncio.AsyncioGspreadClientManager(_make_credentials)
    agc  = await agcm.authorize()

    spreadsheet = await agc.open_by_key(settings.GOOGLE_SPREADSHEET_ID)

    # Create or clear the worksheet
    sheet_title = tournament.name[:100]  # Sheets tab name limit
    try:
        worksheet = await spreadsheet.worksheet(sheet_title)
        await worksheet.clear()
    except Exception:
        worksheet = await spreadsheet.add_worksheet(
            title=sheet_title, rows=500, cols=20
        )

    # Get the numeric sheet ID for formatting requests
    # In gspread-asyncio 2.0.0 the underlying sync object is at .ws
    sheet_id = worksheet.ws.id

    lift_types = tournament.lift_types
    headers    = _build_column_headers(lift_types)
    rankings   = compute_rankings(participants, tournament.tournament_type)

    all_rows: list[list] = []
    format_requests: list[dict] = []
    current_row = 4  # 1-indexed

    # ── Title rows ────────────────────────────────────────────────────────────
    all_rows.append([f"🏆 {tournament.name}  |  {tournament.type_label}"])
    all_rows.append([f"Экспорт: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"])
    all_rows.append([])  # blank

    # ── Per-category data ─────────────────────────────────────────────────────
    for ranking in rankings:
        cat_name = (
            ranking.category.display_name if ranking.category else "Без категории"
        )

        # Category header row
        all_rows.append([cat_name])
        format_requests.append(
            _fmt_range(sheet_id, current_row, 1, current_row, len(headers) + 1,
                       bg=COLOUR["cat_bg"], bold=True)
        )
        current_row += 1

        # Column header row
        all_rows.append(["Место"] + headers)
        format_requests.append(
            _fmt_range(sheet_id, current_row, 1, current_row, len(headers) + 1,
                       bg=COLOUR["header_bg"], fg=COLOUR["header_fg"], bold=True)
        )
        current_row += 1

        # Athlete rows
        for r in ranking.results:
            all_rows.append(_build_athlete_row(r, lift_types))
            if r.place and r.place <= 3:
                format_requests.append(
                    _fmt_range(sheet_id, current_row, 1, current_row,
                               len(headers) + 1,
                               bg=MEDAL_COLOURS[r.place - 1],
                               bold=(r.place == 1))
                )
            current_row += 1

        all_rows.append([])  # blank separator
        current_row += 1

    # ── Write data ────────────────────────────────────────────────────────────
    # gspread 6.x: update(values, range_name) — arguments swapped vs 5.x
    await worksheet.update(all_rows, "A1")

    # ── Apply formatting (best-effort) ────────────────────────────────────────
    if format_requests:
        try:
            await spreadsheet.batch_update({"requests": format_requests})
        except Exception as fmt_err:
            logger.warning("Could not apply formatting: %s", fmt_err)

    return f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SPREADSHEET_ID}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_column_headers(lift_types: List[str]) -> List[str]:
    headers = ["Атлет", "Вес тела"]
    labels  = TournamentType.LIFT_LABELS
    for lt in lift_types:
        lbl = labels.get(lt, lt.capitalize())
        headers += [f"{lbl} 1", f"{lbl} 2", f"{lbl} 3", f"{lbl} лучший"]
    headers.append("Тоталл")
    return headers


def _build_athlete_row(result: AthleteResult, lift_types: List[str]) -> list:
    p   = result.participant
    row = [str(result.place) if result.place else "—", p.full_name, p.bodyweight]

    attempt_map = {
        (a.lift_type, a.attempt_number): a for a in p.attempts
    }
    for lt in lift_types:
        for num in (1, 2, 3):
            a = attempt_map.get((lt, num))
            if a and a.weight_kg:
                mark = "✓" if a.result == AttemptResult.GOOD else (
                       "✗" if a.result == AttemptResult.BAD else "")
                row.append(f"{a.weight_kg:g}{mark}")
            else:
                row.append("—")
        best = result.lift_totals.get(lt)
        row.append(f"{best:g}" if best else "—")

    row.append(f"{result.total:g}" if result.total else "—")
    return row


def _fmt_range(
    sheet_id: int,
    start_row: int,
    start_col: int,
    end_row: int,
    end_col: int,
    bg: Optional[dict] = None,
    fg: Optional[dict] = None,
    bold: bool = False,
) -> dict:
    """Build a Sheets API repeatCell request dict."""
    fmt: dict = {}
    if bg:
        fmt["backgroundColor"] = bg
    if fg or bold:
        fmt["textFormat"] = {}
        if fg:
            fmt["textFormat"]["foregroundColor"] = fg
        if bold:
            fmt["textFormat"]["bold"] = True

    return {
        "repeatCell": {
            "range": {
                "sheetId":          sheet_id,
                "startRowIndex":    start_row - 1,
                "endRowIndex":      end_row,
                "startColumnIndex": start_col - 1,
                "endColumnIndex":   end_col,
            },
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }
