"""
SPORTBAZA — High-End Powerlifting Tournament Management Bot
Entry point: creates the bot, registers routers + middleware, handles graceful shutdown.
"""
import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot.config import settings
from bot.middlewares import DatabaseMiddleware, AdminMiddleware
from bot.models.base import engine, Base
from sqlalchemy import text

# ── Handlers ──────────────────────────────────────────────────────────────────
from bot.handlers.common import router as common_router
from bot.handlers.registration import router as registration_router
from bot.handlers.athlete import router as athlete_router
from bot.handlers.athlete_weights import router as athlete_weights_router
from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.tournament import router as admin_tournament_router
from bot.handlers.admin.scoring import router as admin_scoring_router
from bot.handlers.admin.export import router as admin_export_router
from bot.handlers.admin.analytics import router as admin_analytics_router
from bot.handlers.fallback import router as fallback_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create all database tables on startup."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Incremental migrations for existing databases (idempotent — errors are swallowed)
        async with engine.begin() as conn:
            for sql in [
                "ALTER TABLE participants ADD COLUMN age_category VARCHAR(20)",
            ]:
                try:
                    await conn.execute(text(sql))
                except Exception:
                    pass  # Column already exists (new DB created via create_all)
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
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AdminMiddleware())

    # ── Routers — order matters for handler priority ──────────────────────────
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(athlete_router)
    dp.include_router(athlete_weights_router)

    # Admin routers
    dp.include_router(admin_panel_router)
    dp.include_router(admin_tournament_router)
    dp.include_router(admin_scoring_router)
    dp.include_router(admin_export_router)
    dp.include_router(admin_analytics_router)

    # !! Must be last — catches any callback not handled above !!
    dp.include_router(fallback_router)

    return dp


async def main() -> None:
    logger.info("Starting SPORTBAZA bot…")
    await create_tables()

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
        await bot.session.close()
        await engine.dispose()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
