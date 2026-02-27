# SPORTBAZA — High-End Event Management System with Premium UX

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.13-green)](https://aiogram.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)](https://www.sqlalchemy.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet)](https://railway.app/)

A production-ready Telegram bot for managing powerlifting competitions — from athlete registration through live real-time scoring to automated Google Sheets export and anonymized analytics reporting.

---

## ✨ Feature Highlights

| Feature | Details |
|---|---|
| **Inline-first UX** | Zero mandatory text input for navigation; FSM only where unavoidable (name, weight) |
| **Dynamic menus** | Context-aware panels: Athlete Cabinet vs Admin Panel, adapts to tournament phase |
| **Tournament configurator** | Supports **SBD** (classic powerlifting), **Bench Press**, **Deadlift**, and **Push-Pull** formats |
| **Live Scoring** | Digital judges' desk with ✅/❌ buttons; keyboard updates in-place on every judgement |
| **Push notifications** | Athletes receive styled attempt results + live total breakdown in real time |
| **Ranking engine** | IPF-compliant: best lift per discipline, tie-break by bodyweight, bomb-out detection |
| **Google Sheets export** | Async export with gold/silver/bronze colour-coding for top-3, auto-structured layout |
| **Academic Impact Report** | Anonymized Accuracy %, total tonnage, demographic split, per-category averages |
| **Railway / Docker** | Multi-stage Dockerfile, `docker-compose.yml`, `SIGTERM` graceful shutdown |

---

## 🏗 Architecture

```
SPORTBAZA/
├── bot/
│   ├── main.py               # Dispatcher setup, graceful shutdown
│   ├── config.py             # Pydantic-settings config (env vars)
│   │
│   ├── models/               # SQLAlchemy ORM (async)
│   │   ├── base.py           #   Engine + session factory
│   │   └── models.py         #   User, Tournament, WeightCategory, Participant, Attempt
│   │
│   ├── states/               # aiogram FSM state groups
│   │   ├── registration_states.py
│   │   └── admin_states.py
│   │
│   ├── keyboards/            # Inline keyboard builders
│   │   ├── callbacks.py      #   CallbackData factories (all prefixes ≤5 chars)
│   │   ├── main_menu.py
│   │   ├── registration_kb.py
│   │   ├── admin_kb.py
│   │   └── scoring_kb.py     #   Live judges' panel
│   │
│   ├── middlewares/
│   │   ├── db_middleware.py  #   Inject AsyncSession → handler data
│   │   └── auth_middleware.py#   Inject is_admin flag; IsAdmin filter
│   │
│   ├── services/             # Pure async business-logic layer
│   │   ├── tournament_service.py   # All DB queries
│   │   ├── ranking_service.py      # IPF ranking algorithm
│   │   ├── notification_service.py # Athlete push messages
│   │   ├── sheets_service.py       # Google Sheets async export
│   │   └── analytics_service.py    # Academic Impact Report
│   │
│   └── handlers/
│       ├── common.py         # /start, main menu routing
│       ├── registration.py   # Athlete FSM registration flow
│       ├── athlete.py        # Personal cabinet, withdraw
│       └── admin/
│           ├── panel.py      # Admin home, participant management
│           ├── tournament.py # Create / open / start / finish tournaments
│           ├── scoring.py    # Live scoring FSM
│           ├── export.py     # Results display + Sheets export
│           └── analytics.py  # Impact Report
│
├── Dockerfile                # Multi-stage, non-root user
├── docker-compose.yml        # Bot + PostgreSQL with healthchecks
├── requirements.txt
└── .env.example
```

---

## ⚡ Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd SPORTBAZA
cp .env.example .env
# Fill in BOT_TOKEN, ADMIN_IDS in .env
```

### 2. Run locally (SQLite — no Postgres needed)

```bash
pip install -r requirements.txt
python -m bot.main
```

### 3. Run with Docker Compose (PostgreSQL)

```bash
docker-compose up --build
```

---

## 🌐 Deploy to Railway

1. Push repository to GitHub.
2. Create a new Railway project → **Deploy from GitHub**.
3. Add **PostgreSQL** plugin — Railway auto-injects `DATABASE_URL`.
4. Set environment variables: `BOT_TOKEN`, `ADMIN_IDS`, optionally `GOOGLE_*`.
5. Railway uses the `Dockerfile` automatically.

---

## 🔧 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram Bot token from @BotFather |
| `ADMIN_IDS` | ✅ | Comma-separated Telegram user IDs with admin access |
| `DATABASE_URL` | ⚪ | PostgreSQL URL (defaults to local SQLite) |
| `GOOGLE_CREDENTIALS_JSON` | ⚪ | Service account JSON (single line) for Sheets export |
| `GOOGLE_SPREADSHEET_ID` | ⚪ | Target spreadsheet ID from its URL |

---

## 🏋️ Tournament Lifecycle

```
DRAFT → REGISTRATION → ACTIVE → FINISHED
  │           │            │
  │     Athletes join   Admin judges attempts
  │     (self-service)  Athletes get push notifications
  │
  └─ Admin configures categories (IPF standard sets)
```

### Tournament Types & Disciplines

| Code | Name | Disciplines |
|---|---|---|
| `SBD` | Classic Powerlifting | Squat · Bench Press · Deadlift |
| `BP` | Bench Press | Bench Press |
| `DL` | Deadlift | Deadlift |
| `PP` | Push-Pull | Bench Press · Deadlift |

---

## 📊 Ranking Algorithm

```python
# IPF-compliant ranking within each weight/gender category
sort_key = (-total, bodyweight)   # higher total wins; lighter BW breaks ties
```

- Athletes who bomb out (0 successful attempts in a required lift) receive `total = None` and are ranked last.
- Weight categories follow IPF naming: `-59`, `-66`, … `120+` for men; `-47` … `84+` for women.

---

## 🔬 Academic Impact Report (Data Engineering Showcase)

The analytics module (`services/analytics_service.py`) implements a data pipeline that:

1. **Filters** active (non-withdrawn) participants.
2. **Aggregates** attempt outcomes per discipline → Accuracy %.
3. **Computes** total tonnage = Σ(all successful lift weights).
4. **Collects** valid totals → median / max / min statistics.
5. **Groups** by category → per-category average totals.

All algorithm comments are in **English** to demonstrate data-engineering competency for the US job market.

---

## 🛡 Security

- Admin functions protected by `IsAdmin` filter — checks against `ADMIN_IDS` env var.
- No admin telegram ID is hardcoded; configuration is 100% environment-driven.
- Non-root Docker user (`appuser`) for container security.
- DB session commit/rollback handled by middleware — no partial writes on handler exceptions.

---

## 📄 License

MIT — free to use for competitions, sports clubs and hackathons.

---

*Built with aiogram 3.x · SQLAlchemy 2.0 · Pydantic-Settings · gspread-asyncio*
