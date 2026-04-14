"""
In-memory OTP store with automatic expiry.
Sufficient for single-instance ECS; upgrade to Redis if scaling horizontally.
"""
import secrets
import time
import threading
from typing import Dict, Optional

_store: Dict[str, dict] = {}  # {email: {"otp": str, "expires_at": float, "attempts": int}}
_lock = threading.Lock()

OTP_EXPIRY_SECONDS = 600  # 10 minutes
MAX_ATTEMPTS = 5  # lock out after 5 wrong guesses
MIN_RESEND_SECONDS = 60  # prevent spamming OTP requests


def generate_otp(email: str) -> Optional[str]:
    """Generate a 6-digit OTP. Returns None if called too soon (rate limit)."""
    key = email.lower()
    otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
    with _lock:
        existing = _store.get(key)
        if existing and time.time() < existing.get("cooldown", 0):
            return None  # rate limited
        _store[key] = {
            "otp": otp,
            "expires_at": time.time() + OTP_EXPIRY_SECONDS,
            "attempts": 0,
            "cooldown": time.time() + MIN_RESEND_SECONDS,
        }
    return otp


def verify_otp(email: str, otp: str) -> bool:
    """Verify an OTP. Returns True if valid, False otherwise. Deletes on success."""
    key = email.lower()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return False
        if time.time() > entry["expires_at"]:
            del _store[key]
            return False
        if entry["attempts"] >= MAX_ATTEMPTS:
            del _store[key]  # too many wrong guesses, force re-request
            return False
        if entry["otp"] != otp:
            entry["attempts"] += 1
            return False
        del _store[key]
        return True


def cleanup_expired():
    """Remove all expired entries."""
    now = time.time()
    with _lock:
        expired = [k for k, v in _store.items() if now > v["expires_at"]]
        for k in expired:
            del _store[k]
