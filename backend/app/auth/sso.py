"""
SSO middleware — extracts authenticated username from:
  1. REMOTE_USER header (set by IIS/Apache Kerberos/NTLM)
  2. X-Dev-User header  (DEV_MODE only)
  3. __dev_user cookie  (DEV_MODE only — set by /dev/ test page)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

DEV_COOKIE = "__dev_user"


class SSOMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        remote_user = (
            request.headers.get("REMOTE_USER")
            or request.headers.get("X-Remote-User")
            or request.scope.get("REMOTE_USER")
        )

        if not remote_user and settings.DEV_MODE:
            remote_user = (
                request.headers.get("X-Dev-User")
                or request.cookies.get(DEV_COOKIE)
            )

        request.state.remote_user = remote_user or None
        return await call_next(request)


def get_remote_user(request: Request) -> str | None:
    return getattr(request.state, "remote_user", None)
