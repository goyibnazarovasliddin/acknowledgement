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

# Document-flow user session (set after successful AD login on a share link)
DOC_COOKIE_PREFIX = "ack_user_"
DOC_SESSION_HOURS = 4
_doc_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="doc-session")


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


# ---------------------------------------------------------------------------
# Document-flow session — holds the AD identity for one share link
# ---------------------------------------------------------------------------
def _doc_cookie(token: str) -> str:
    return f"{DOC_COOKIE_PREFIX}{token}"


def create_doc_session(response: Response, token: str, user_info: dict) -> None:
    payload = {
        "u": user_info.get("username"),
        "fn": user_info.get("full_name"),
        "d": user_info.get("department"),
        "p": user_info.get("position"),
        "e": user_info.get("email"),
    }
    value = _doc_signer.dumps(payload)
    response.set_cookie(
        _doc_cookie(token),
        value,
        httponly=True,
        samesite="lax",
        max_age=int(timedelta(hours=DOC_SESSION_HOURS).total_seconds()),
        secure=not settings.DEV_MODE,
    )


def get_doc_session(request: Request, token: str) -> Optional[dict]:
    raw = request.cookies.get(_doc_cookie(token))
    if not raw:
        return None
    try:
        max_age = int(timedelta(hours=DOC_SESSION_HOURS).total_seconds())
        data = _doc_signer.loads(raw, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return {
        "username": data.get("u"),
        "full_name": data.get("fn"),
        "department": data.get("d"),
        "position": data.get("p"),
        "email": data.get("e"),
    }


def clear_doc_session(response: Response, token: str) -> None:
    response.delete_cookie(_doc_cookie(token))
