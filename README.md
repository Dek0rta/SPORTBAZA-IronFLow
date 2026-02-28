# SPORTBAZA Iron Flow — High-End Powerlifting Tournament Management System

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.13-green)](https://aiogram.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)](https://www.sqlalchemy.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet)](https://railway.app/)

A production-ready Telegram bot for managing powerlifting competitions — from athlete registration and QR check-in through live real-time scoring, multi-formula coefficient rankings, and a public all-time records vault.

---

## ✨ Feature Highlights

| Feature | Details |
|---|---|
| **Inline-first UX** | Zero mandatory text input for navigation; FSM only where unavoidable |
| **Dynamic menus** | Context-aware panels: Athlete Cabinet vs Admin Panel, adapts to tournament phase |
| **Tournament configurator** | Supports **SBD**, **Bench Press**, **Deadlift**, and **Push-Pull** formats |
| **Live Scoring** | Digital judges' desk with ✅/❌ buttons; keyboard updates in-place |
| **Push notifications** | Athletes receive styled attempt results + live total breakdown |
| **Ranking Engine v2** | IPF-compliant + Wilks/DOTS/Glossbrenner/IPF GL coefficient rankings |
| **Overall Champion** | Cross-category absolute ranking by selected formula |
| **Division Rankings** | Age-division → weight sub-division hierarchy |
| **Public Records Vault** | All-time platform records with inline filtered navigation |
| **QR Check-in** | Auto-generated QR ticket on registration; admin UUID scanner |
| **Performance Delta** | "Your bench press improved +5.0% over 3 competitions" |
| **World Benchmark** | "You are stronger than 72% of athletes in your category worldwide" |
| **Rate Limiting** | 30 requests/60 s per user — flood-proof middleware |
| **Google Sheets export** | Async export with colour-coding for top-3, auto-structured layout |
| **Academic Impact Report** | Accuracy %, total tonnage, demographic split, per-category averages |
| **Railway / Docker** | Multi-stage Dockerfile, `docker-compose.yml`, SIGTERM graceful shutdown |

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
│   │   └── models.py         #   User, Tournament, WeightCategory, Participant,
│   │                         #   Attempt, PlatformRecord + FormulaType constants
│   │
│   ├── states/               # aiogram FSM state groups
│   │   ├── registration_states.py
│   │   └── admin_states.py   #   Includes AdminQrScanStates
│   │
│   ├── keyboards/            # Inline keyboard builders
│   │   ├── callbacks.py      #   All CallbackData factories (prefixes ≤5 chars)
│   │   ├── main_menu.py      #   Includes Records Vault + QR Check-in buttons
│   │   ├── registration_kb.py
│   │   ├── admin_kb.py       #   Includes formula_select_kb()
│   │   ├── scoring_kb.py     #   Live judges' panel
│   │   └── records_kb.py     #   Records Vault navigation (NEW)
│   │
│   ├── middlewares/
│   │   ├── db_middleware.py  #   Inject AsyncSession → handler data
│   │   ├── auth_middleware.py#   Inject is_admin flag; IsAdmin filter
│   │   └── rate_limit_middleware.py  # Sliding-window rate limiter (NEW)
│   │
│   ├── services/             # Pure async business-logic layer
│   │   ├── tournament_service.py   # All DB queries + set_tournament_formula()
│   │   ├── ranking_service.py      # IPF + formula rankings (v2)
│   │   ├── formula_service.py      # Wilks/DOTS/Glossbrenner/IPF GL (NEW)
│   │   ├── records_service.py      # Records Vault CRUD (NEW)
│   │   ├── qr_service.py           # QR code generation (NEW)
│   │   ├── notification_service.py # Athlete push messages
│   │   ├── sheets_service.py       # Google Sheets async export
│   │   └── analytics_service.py    # Academic Impact Report
│   │
│   └── handlers/
│       ├── common.py         # /start, main menu routing
│       ├── registration.py   # Athlete FSM registration + QR ticket send
│       ├── athlete.py        # Personal cabinet + performance delta + percentile
│       ├── athlete_weights.py# Athlete weight declaration
│       ├── records.py        # Public Records Vault /records command (NEW)
│       └── admin/
│           ├── panel.py      # Admin home, participant management
│           ├── tournament.py # Create / open / start / finish tournaments
│           ├── scoring.py    # Live scoring FSM
│           ├── export.py     # Results + formula scores + Records Vault update
│           ├── analytics.py  # Impact Report
│           ├── formula.py    # Scoring formula selector (NEW)
│           └── qr_scanner.py # QR check-in scanner (NEW)
│
├── migrations/               # Alembic migrations (NEW)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_iron_flow_v2.py
│
├── alembic.ini               # Alembic config (NEW)
├── Dockerfile                # Multi-stage, non-root user
├── docker-compose.yml        # Bot + PostgreSQL with healthchecks
├── requirements.txt          # + segno (QR encoder)
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

### 4. Run Alembic migrations (existing DB)

```bash
alembic upgrade head
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
  │           │            │         │
  │     Athletes join   Admin judges  Records Vault
  │     QR tickets      attempts     auto-updated
  │     generated       + formula
  │                     scores shown
  └─ Admin configures categories (IPF standard sets)
       + selects scoring formula
```

### Tournament Types & Disciplines

| Code | Name | Disciplines |
|---|---|---|
| `SBD` | Classic Powerlifting | Squat · Bench Press · Deadlift |
| `BP` | Bench Press | Bench Press |
| `DL` | Deadlift | Deadlift |
| `PP` | Push-Pull | Bench Press · Deadlift |

---

## 🔢 Ranking Engine v2

### Algorithm Overview

```
1. Compute each athlete's best lift per discipline.
2. Calculate competition total (sum of bests; bomb-out → total=None).
3. Apply the tournament's active scoring formula:
     formula_score = f(total, bodyweight, gender)
4. Sort by: formula_score DESC → bodyweight ASC (tie-break).
5. Assign places: ties share the same place number.
```

### Scoring Formulas

| Formula | Description | Best for |
|---|---|---|
| `total` | Raw sum in kg — no coefficient | Category-level comparison |
| `wilks` | **Wilks 2020** polynomial | All-time comparison; IPF-endorsed |
| `dots` | **DOTS** polynomial | Age-independent comparison |
| `glossbrenner` | Piecewise power-law | Traditional raw powerlifting |
| `ipf_gl` | **IPF GL (Goodlift)** | Current IPF competition formula |

**Admin taps "🔢 Формула" in the tournament panel to switch the active formula at any time.**

### Hierarchy of Results

```
Overall (Absolute) Champion
  └─ All athletes ranked by formula_score regardless of weight class

Age Divisions (Sub-Junior / Junior / Open / Masters 1–4)
  └─ Weight Sub-Divisions (-59 / -66 / -74 / … / 120+)
       └─ Athletes ranked within each weight+gender category
```

### Result Display Format

```
🥇 Иванов Иван — 605 кг [DOTS: 412.50]
🥈 Петров Пётр — 595 кг [DOTS: 408.30]  _93.0 кг_
🥉 Сидоров Сидор — 580 кг [DOTS: 401.15]
```

### Алгоритм (русский)

```
1. Рассчитать лучший подход в каждой дисциплине.
2. Вычислить сумму (тотал). Бомб-аут → тотал = None (последнее место).
3. Применить активную формулу (Wilks / DOTS / Glossbrenner / IPF GL).
4. Сортировка: балл по формуле убывает → при равенстве — собственный вес возрастает.
5. Присвоить места: равный балл и вес → одинаковое место.

Абсолютный зачёт: все атлеты вне зависимости от весовой категории.
Дивизионный зачёт: возрастная категория → весовая категория.
```

---

## 🏛️ Public Records Vault

### Database Structure

Table `platform_records`:
| Column | Type | Description |
|---|---|---|
| `lift_type` | VARCHAR(20) | squat / bench / deadlift / total |
| `weight_kg` | FLOAT | Record weight in kg |
| `gender` | VARCHAR(5) | M / F |
| `age_category` | VARCHAR(20) | AgeCategory.* |
| `weight_category_name` | VARCHAR(50) | IPF weight class (e.g. "-93") |
| `athlete_name` | VARCHAR(255) | Athlete full name |
| `tournament_name` | VARCHAR(255) | Tournament where record was set |
| `set_at` | DATETIME | Date of record |

The `(lift_type, gender, age_category, weight_category_name)` combination is **unique** — only one all-time record per slot.

### Record Update Logic

Records are automatically updated when a tournament is exported or finished:
1. For each non-withdrawn participant, check their best lift per discipline.
2. Compare against the existing platform record for `(lift_type, gender, age_category, weight_category_name)`.
3. If the new result exceeds the existing record — update it.

### User Interface

```
/records  OR  🥇 База рекордов (main menu button)

  → Gender filter (М / Ж)
      → Age category filter
          → Weight category filter
              → Records table for selected slot
```

### База рекордов (русский)

Команда `/records` или кнопка **🥇 База рекордов** открывает публичный архив рекордов платформы.

**Фильтрация:**
- По полу (Мужчины / Женщины)
- По возрастному дивизиону (Юниоры / Молодёжь / Открытая / Мастера)
- По весовой категории (−47 … 120+)

Рекорды автоматически обновляются после завершения каждого турнира.

---

## 📷 QR Check-in System

### Athlete Flow
1. Athlete completes registration FSM.
2. Bot generates a UUID4 QR ticket and sends it as a photo.
3. Athlete saves the QR image to their phone.

### Admin Flow
1. Admin taps **📷 QR Check-in** in the admin panel.
2. Bot enters `AdminQrScanStates.waiting_token`.
3. Admin scans athlete's QR with any camera app → copies the UUID.
4. Admin pastes the UUID into the bot.
5. Bot looks up the participant and marks `checked_in = True`.

---

## 📈 Performance Delta & World Benchmark

### Performance Delta
Shows improvement across tournaments for the same athlete:
```
📈 Жим лёжа: +5.0% за 3 соревнования (+12.5 кг | текущий рекорд: 150 кг)
```
Displayed in the athlete's profile card after a finished tournament.

### World Benchmark
Compares athlete's total to a reference distribution from competitive raw powerlifting:
```
🌍 Мировой рейтинг: Вы сильнее, чем 72% атлетов в вашей категории
```
Based on normal distribution approximation over OpenPowerlifting reference medians.

---

## 🛡 Security

- Admin functions protected by `IsAdmin` filter — checks against `ADMIN_IDS` env var.
- **Rate limiting**: 30 requests / 60 seconds per user (sliding window).
- **Strict input validation** in all FSM text handlers (bodyweight, weight, full name).
- No admin telegram ID is hardcoded; configuration is 100% environment-driven.
- Non-root Docker user (`appuser`) for container security.
- DB session commit/rollback handled by middleware — no partial writes on exceptions.
- QR tokens use UUID4 — cryptographically random, not guessable.

---

## 🔬 Academic Impact Report (Data Engineering Showcase)

The analytics module (`services/analytics_service.py`) implements a data pipeline that:

1. **Filters** active (non-withdrawn) participants.
2. **Aggregates** attempt outcomes per discipline → Accuracy %.
3. **Computes** total tonnage = Σ(all successful lift weights).
4. **Collects** valid totals → median / max / min statistics.
5. **Groups** by category → per-category average totals.

All algorithm comments are in **English** to demonstrate data-engineering competency.

---

## 📄 License

MIT — free to use for competitions, sports clubs and hackathons.

---

*Built with aiogram 3.x · SQLAlchemy 2.0 · Pydantic-Settings · gspread-asyncio · segno*
