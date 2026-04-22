"""
DEV_MODE only — test user flow without Kerberos.
Mounts at /dev/  — blocked in production (DEV_MODE=false).
"""
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.sso import DEV_COOKIE
from app.config import settings

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "templates"

router = APIRouter(prefix="/dev")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _guard():
    if not settings.DEV_MODE:
        from fastapi import HTTPException
        raise HTTPException(404)


@router.get("/", response_class=HTMLResponse)
async def dev_home(request: Request):
    _guard()
    current = request.cookies.get(DEV_COOKIE, "")
    return templates.TemplateResponse(
        "dev/index.html",
        {"request": request, "current_user": current},
    )


@router.post("/set-user")
async def set_user(username: str = Form(...)):
    _guard()
    response = RedirectResponse("/dev/", status_code=302)
    response.set_cookie(DEV_COOKIE, username, httponly=True, samesite="lax")
    return response


@router.post("/clear-user")
async def clear_user():
    _guard()
    response = RedirectResponse("/dev/", status_code=302)
    response.delete_cookie(DEV_COOKIE)
    return response
