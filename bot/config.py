"""
Central configuration via pydantic-settings.
All secrets are read from environment variables / .env file.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    BOT_TOKEN: str

    # Raw comma-separated admin IDs, e.g. "123,456"
    ADMIN_IDS: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sportbaza"

    @property
    def async_database_url(self) -> str:
        """
        Railway injects DATABASE_URL as 'postgresql://...'
        SQLAlchemy async requires 'postgresql+asyncpg://...'
        This property fixes the prefix automatically.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            return url.replace("://", "+asyncpg://", 1)
        return url

    # ── Google Sheets (optional) ──────────────────────────────────────────────
    GOOGLE_CREDENTIALS_JSON: Optional[str] = None
    GOOGLE_SPREADSHEET_ID: Optional[str] = None

    # ─────────────────────────────────────────────────────────────────────────

    @property
    def admin_ids_list(self) -> list[int]:
        """Parse ADMIN_IDS env var to a list of integers."""
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

    @property
    def google_credentials(self) -> dict:
        """Deserialize Google service-account credentials."""
        if self.GOOGLE_CREDENTIALS_JSON:
            return json.loads(self.GOOGLE_CREDENTIALS_JSON)
        return {}

    @property
    def sheets_enabled(self) -> bool:
        return bool(self.GOOGLE_CREDENTIALS_JSON and self.GOOGLE_SPREADSHEET_ID)


settings = Settings()
