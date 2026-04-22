"""
Signed session cookie for admin panel.
Uses itsdangerous.URLSafeTimedSerializer — no DB, no JWT dep.
"""
from datetime import timedelta
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

COOKIE_NAME = "ack_admin"
_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="admin-session")


def create_session(response: Response, username: str) -> None:
    token = _signer.dumps({"u": username})
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=int(timedelta(hours=settings.ADMIN_SESSION_HOURS).total_seconds()),
        secure=not settings.DEV_MODE,
    )


def get_session_user(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        max_age = int(timedelta(hours=settings.ADMIN_SESSION_HOURS).total_seconds())
        data = _signer.loads(token, max_age=max_age)
        return data.get("u")
    except (SignatureExpired, BadSignature):
        return None


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
