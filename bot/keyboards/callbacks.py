"""
Centralized CallbackData factories.
Telegram limits callback_data to 64 bytes — all prefixes are kept short.
"""
from typing import Optional

from aiogram.filters.callback_data import CallbackData


class MainMenuCb(CallbackData, prefix="mm"):
    action: str


class TournamentCb(CallbackData, prefix="trn"):
    action: str           # list | view | create | open_reg | start | finish | delete
    tid: int = 0          # tournament id


class CategoryCb(CallbackData, prefix="cat"):
    action: str           # toggle | confirm | back
    tid: int = 0          # tournament id
    cid: int = 0          # category id (0 = N/A)
    gender: str = ""


class ParticipantCb(CallbackData, prefix="par"):
    action: str           # view | confirm | withdraw | list | select_scoring
    pid: int = 0          # participant id
    tid: int = 0          # tournament id


class AttemptCb(CallbackData, prefix="att"):
    action: str           # set_weight | good | bad | cancel_result
    aid: int = 0          # attempt id
    pid: int = 0          # participant id (for context return)


class ScoringNavCb(CallbackData, prefix="snav"):
    action: str           # prev | next | list | back
    tid: int = 0
    pid: int = 0          # current participant id


class AdminPanelCb(CallbackData, prefix="adm"):
    action: str           # tournaments | scoring | export | analytics | participants | qr_scan


class AnalyticsCb(CallbackData, prefix="anl"):
    action: str           # report
    tid: int = 0


class ExportCb(CallbackData, prefix="exp"):
    action: str           # sheets
    tid: int = 0


class RecordsCb(CallbackData, prefix="rcd"):
    action: str           # list | filter_gender | filter_age | filter_weight | reset
    gender: str = ""
    age_cat: str = ""
    wcat: str = ""
    page: int = 0


class FormulaSelectCb(CallbackData, prefix="frm"):
    action: str           # set | toggle
    tid: int = 0
    formula: Optional[str] = None


class QrCheckinCb(CallbackData, prefix="qrc"):
    action: str           # scan | confirm | cancel
    pid: int = 0
