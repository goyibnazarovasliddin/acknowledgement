"""
Security helpers: constant-time admin check, in-memory login rate limiting,
production-config validation, and the Content-Security-Policy string.

Kept dependency-free (stdlib only) so it works in every deploy mode.
"""
import secrets
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List

from app.config import settings


# ---------------------------------------------------------------------------
# Admin credential check (constant-time, avoids username/password timing leak)
# ---------------------------------------------------------------------------
def verify_admin(username: str, password: str) -> bool:
    u_ok = secrets.compare_digest(username or "", settings.ADMIN_USERNAME)
    p_ok = secrets.compare_digest(password or "", settings.ADMIN_PASSWORD)
    return u_ok and p_ok


# ---------------------------------------------------------------------------
# In-memory login rate limiter / lockout (per client IP)
# Stateless app, single process — good enough to blunt online brute force.
# For multi-worker/multi-host, move this to Redis.
# ---------------------------------------------------------------------------
LOGIN_WINDOW_SECONDS = 300   # rolling window
LOGIN_MAX_FAILURES = 5       # failures allowed per window before lockout

_failures: Dict[str, Deque[float]] = defaultdict(deque)


def _prune(dq: Deque[float], now: float) -> None:
    while dq and now - dq[0] > LOGIN_WINDOW_SECONDS:
        dq.popleft()


def login_blocked(ip: str) -> bool:
    dq = _failures[ip]
    _prune(dq, time.time())
    return len(dq) >= LOGIN_MAX_FAILURES


def record_login_failure(ip: str) -> None:
    dq = _failures[ip]
    now = time.time()
    _prune(dq, now)
    dq.append(now)


def reset_login(ip: str) -> None:
    _failures.pop(ip, None)


# ---------------------------------------------------------------------------
# Production config validation — refuse to boot with insecure defaults
# ---------------------------------------------------------------------------
_INSECURE_SECRET_KEYS = {
    "change-me-in-production",
    "dev-secret",
    "dev-secret-do-not-use-in-production",
    "CHANGE_ME_MINIMUM_32_CHARS_RANDOM_STRING",
}
_INSECURE_ADMIN_PASSWORDS = {"admin123", "admin", "password", ""}
_INSECURE_LDAP_PASSWORDS = {"PASSWORD", "changeme", "CHANGE_ME_AD_SERVICE_ACCOUNT_PASSWORD", ""}


def check_dev_mode() -> "tuple[List[str], List[str]]":
    """DEV_MODE enables a login bypass (any user + DEV_LOGIN_PASSWORD).
    Returns (fatal, warnings)."""
    fatal: List[str] = []
    warn: List[str] = []
    if settings.DEV_MODE:
        warn.append(
            "DEV_MODE=true — AD login bypass is ACTIVE (any username + DEV_LOGIN_PASSWORD). "
            "Never enable in production."
        )
        # Postgres + DEV_MODE almost certainly means a production deploy with the
        # bypass accidentally left on — refuse to boot.
        if settings.DATABASE_URL.startswith("postgresql"):
            fatal.append(
                "DEV_MODE=true together with a PostgreSQL database — refusing to start "
                "(production deploy with the auth bypass enabled)."
            )
    return fatal, warn


def validate_production_settings() -> List[str]:
    """Return a list of fatal misconfigurations (empty == OK). Skipped in DEV_MODE."""
    if settings.DEV_MODE:
        return []
    problems: List[str] = []
    if settings.SECRET_KEY in _INSECURE_SECRET_KEYS or len(settings.SECRET_KEY) < 32:
        problems.append("SECRET_KEY is a default or shorter than 32 chars — forgeable session cookies")
    if settings.ADMIN_PASSWORD in _INSECURE_ADMIN_PASSWORDS:
        problems.append("ADMIN_PASSWORD is a default/weak value")
    if settings.LDAP_PASSWORD in _INSECURE_LDAP_PASSWORDS:
        problems.append("LDAP_PASSWORD is a default/empty value")
    return problems


# ---------------------------------------------------------------------------
# Content-Security-Policy
# Allows the two CDNs the app currently loads (pdf.js, Chart.js) + inline
# scripts/styles the templates use. frame-ancestors 'none' blocks clickjacking
# of the acknowledge action; object-src 'none' blocks plugin-based injection.
# ---------------------------------------------------------------------------
# All JS is now self-hosted under /static/vendor — no third-party origins.
# 'unsafe-inline' stays only because templates use inline <script>/<style>.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
