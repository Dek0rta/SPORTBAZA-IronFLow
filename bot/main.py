"""
SPORTBAZA Iron Flow — High-End Powerlifting Tournament Management Bot
Entry point: creates the bot, registers routers + middleware, handles graceful shutdown.
"""
import asyncio
import logging
import os
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot.config import settings
from bot.middlewares import DatabaseMiddleware, AdminMiddleware, RateLimitMiddleware
from bot.models.base import engine, Base
from sqlalchemy import text

# ── Handlers ──────────────────────────────────────────────────────────────────
from bot.handlers.common import router as common_router
from bot.handlers.registration import router as registration_router
from bot.handlers.athlete import router as athlete_router
from bot.handlers.athlete_weights import router as athlete_weights_router
from bot.handlers.records import router as records_router
from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.tournament import router as admin_tournament_router
from bot.handlers.admin.scoring import router as admin_scoring_router
from bot.handlers.admin.export import router as admin_export_router
from bot.handlers.admin.analytics import router as admin_analytics_router
from bot.handlers.admin.formula import router as admin_formula_router
from bot.handlers.admin.qr_scanner import router as admin_qr_router
from bot.handlers.fallback import router as fallback_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create all database tables on startup and run incremental migrations."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Incremental migrations for existing databases (idempotent — errors swallowed)
        _migrations = [
            # v1 migrations
            "ALTER TABLE participants ADD COLUMN age_category VARCHAR(20)",
            # Iron Flow v2 migrations
            "ALTER TABLE tournaments ADD COLUMN scoring_formula VARCHAR(20) DEFAULT 'total'",
            "ALTER TABLE participants ADD COLUMN qr_token VARCHAR(36)",
            "ALTER TABLE participants ADD COLUMN checked_in BOOLEAN DEFAULT FALSE",
            # v2.1
            "ALTER TABLE participants ADD COLUMN opening_weight FLOAT",
            "ALTER TABLE tournaments ADD COLUMN tournament_date VARCHAR(20)",
            # v2.2 — in-app notifications
            ("CREATE TABLE IF NOT EXISTS notifications ("
             "id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, "
             "type VARCHAR(50) NOT NULL, title VARCHAR(255) NOT NULL, body VARCHAR(1000) NOT NULL, "
             "read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT now())"),
        ]
        for sql in _migrations:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists

        logger.info("Database tables ready.")
    except Exception as e:
        logger.critical(
            "❌ Cannot connect to database!\n"
            "   URL: %s\n"
            "   Error: %s\n\n"
            "   → On Railway: add a PostgreSQL plugin (Add Service → Database → PostgreSQL)\n"
            "   → Locally: start PostgreSQL or use SQLite "
            "(DATABASE_URL=sqlite+aiosqlite:///./sportbaza.db)",
            settings.DATABASE_URL.split("@")[-1],   # hide credentials in log
            e,
        )
        sys.exit(1)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # ── Global error handler — ensures callbacks are always answered ──────────
    @dp.errors()
    async def handle_error(event: ErrorEvent) -> None:
        logger.exception("Unhandled error: %s", event.exception)
        update = event.update
        if update.callback_query:
            try:
                await update.callback_query.answer(
                    "⚠️ Произошла ошибка. Попробуйте снова.", show_alert=True
                )
            except Exception:
                pass

    # ── Global middlewares ────────────────────────────────────────────────────
    dp.update.middleware(RateLimitMiddleware(rate=30, period=60.0))
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AdminMiddleware())

    # ── Routers — order matters for handler priority ──────────────────────────
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(athlete_router)
    dp.include_router(athlete_weights_router)
    dp.include_router(records_router)

    # Admin routers
    dp.include_router(admin_panel_router)
    dp.include_router(admin_tournament_router)
    dp.include_router(admin_scoring_router)
    dp.include_router(admin_export_router)
    dp.include_router(admin_analytics_router)
    dp.include_router(admin_formula_router)
    dp.include_router(admin_qr_router)

    # !! Must be last — catches any callback not handled above !!
    dp.include_router(fallback_router)

    return dp


async def main() -> None:
    logger.info("Starting SPORTBAZA Iron Flow bot…")
    await create_tables()

    # ── REST API server (aiohttp, runs alongside the bot) ─────────────────────
    from aiohttp import web as aiohttp_web
    from bot.api.routes import routes as api_routes, cors_middleware

    api_app = aiohttp_web.Application(middlewares=[cors_middleware])
    api_app.add_routes(api_routes)
    api_runner = aiohttp_web.AppRunner(api_app)
    await api_runner.setup()
    api_port = int(os.getenv("PORT", str(settings.API_PORT)))
    await aiohttp_web.TCPSite(api_runner, "0.0.0.0", api_port).start()
    logger.info("API server listening on port %d", api_port)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = build_dispatcher()

    # ── Graceful shutdown on SIGTERM (Railway / Docker) ───────────────────────
    loop = asyncio.get_running_loop()

    shutdown_event = asyncio.Event()

    def _handle_signal():
        logger.info("Received shutdown signal, stopping…")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows does not support add_signal_handler
            pass

    try:
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=False,
        )
    finally:
        logger.info("Shutting down…")
        await api_runner.cleanup()
        await bot.session.close()
        await engine.dispose()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
