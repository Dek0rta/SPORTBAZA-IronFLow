"""
QR-Logistics service for SPORTBAZA Iron Flow.

Generates QR-code tickets for athlete check-in and validates tokens.
Uses `segno` — a pure-Python QR encoder (no native libs required).
"""
from __future__ import annotations

import io
import uuid
from typing import Optional

import segno


def make_qr_token() -> str:
    """Generate a cryptographically random UUID4 token for a participant."""
    return str(uuid.uuid4())


def generate_qr_png(token: str, scale: int = 10, border: int = 2) -> bytes:
    """
    Render a QR code for the given token as a PNG image.

    Parameters
    ----------
    token  : the UUID string to encode
    scale  : pixels per module (default 10 → ~400px for a typical QR)
    border : quiet-zone width in modules

    Returns
    -------
    PNG bytes ready to be sent as a Telegram photo.
    """
    qr  = segno.make_qr(token, error="H")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=border)
    buf.seek(0)
    return buf.read()


def generate_qr_buffered(token: str, scale: int = 10, border: int = 2) -> io.BytesIO:
    """
    Same as generate_qr_png but returns a seeked BytesIO buffer.
    Useful for aiogram's BufferedInputFile.
    """
    qr  = segno.make_qr(token, error="H")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=border)
    buf.seek(0)
    return buf


def validate_token_format(token: str) -> bool:
    """Check that the string looks like a valid UUID4 (basic sanity check)."""
    try:
        val = uuid.UUID(token, version=4)
        return str(val) == token.lower()
    except (ValueError, AttributeError):
        return False
