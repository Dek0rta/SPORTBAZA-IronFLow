import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from bot.config import settings


def verify_webapp_init_data(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData signature. Returns parsed dict or None."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, received_hash):
            return parsed
    except Exception:
        pass
    return None


def parse_tg_user(init_data: str) -> dict | None:
    """Extract user dict from initData. Returns None if invalid."""
    parsed = verify_webapp_init_data(init_data)
    if not parsed:
        return None
    try:
        return json.loads(parsed.get("user", "{}"))
    except (json.JSONDecodeError, AttributeError):
        return None
