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

from bot.config import settings
from bot.middlewares import DatabaseMiddleware, AdminMiddleware
from bot.models.base import engine, Base

# ── Handlers ──────────────────────────────────────────────────────────────────
from bot.handlers.common import router as common_router
from bot.handlers.registration import router as registration_router
from bot.handlers.athlete import router as athlete_router
from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.tournament import router as admin_tournament_router
from bot.handlers.admin.scoring import router as admin_scoring_router
from bot.handlers.admin.export import router as admin_export_router
from bot.handlers.admin.analytics import router as admin_analytics_router

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

    # ── Global middlewares ────────────────────────────────────────────────────
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AdminMiddleware())

    # ── Routers — order matters for handler priority ──────────────────────────
    dp.include_router(common_router)
    dp.include_router(registration_router)
    dp.include_router(athlete_router)

    # Admin routers
    dp.include_router(admin_panel_router)
    dp.include_router(admin_tournament_router)
    dp.include_router(admin_scoring_router)
    dp.include_router(admin_export_router)
    dp.include_router(admin_analytics_router)

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
