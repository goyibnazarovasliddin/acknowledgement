"""
User-facing document flow endpoints.

GET  /d/{token}             — login form (no session) or confirm page (session)
POST /d/{token}/login       — verify AD credentials → create doc session
POST /d/{token}/confirm     — "Ha, bu men" → create attempt (OPENED) → viewer
POST /d/{token}/decline     — "Yo'q, bu men emas" → re-check AD (max 3)
GET  /d/{token}/view        — (viewer is returned by /confirm)
GET  /d/{token}/file        — serve raw file (requires doc session)
POST /d/{token}/acknowledge — finalize attempt → ACKNOWLEDGED
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "templates"

from app.auth.ldap_client import ldap_client
from app.auth.session import create_doc_session, get_doc_session, clear_doc_session
from app.config import settings
from app.database import get_db
from app.models import Document
from app.services import document_service, log_service

logger = logging.getLogger(__name__)

from app.timeutil import fmt_local

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.filters["localdt"] = fmt_local

TEMPLATE_CTX = {
    "scroll_threshold": settings.SCROLL_THRESHOLD,
    "min_view_seconds": settings.MIN_VIEW_SECONDS,
}

_DECLINE_COOKIE = "ack_decline"
_LOGIN_COOKIE = "ack_login"
_MAX_ATTEMPTS = settings.MAX_DECLINE_ATTEMPTS


def _get_doc_or_404(db: Session, token: str) -> Document:
    doc = document_service.get_by_token(db, token)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


# ---------------------------------------------------------------------------
# STEP 1 — open link → login form OR confirm page
# ---------------------------------------------------------------------------
@router.get("/d/{token}", response_class=HTMLResponse)
async def open_document(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    user = get_doc_session(request, token)

    if not user:
        try:
            declined = int(request.cookies.get(f"{_DECLINE_COOKIE}_{token}", "0"))
        except ValueError:
            declined = 0
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "doc": doc,
                "error": None,
                "relogin_attempt": declined or None,
                "max_attempts": _MAX_ATTEMPTS,
            },
        )

    return templates.TemplateResponse(
        "confirm.html",
        {"request": request, "doc": doc, "user": user, **TEMPLATE_CTX},
    )


# ---------------------------------------------------------------------------
# STEP 2 — AD login
# ---------------------------------------------------------------------------
@router.post("/d/{token}/login", response_class=HTMLResponse)
async def login(
    token: str,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(db, token)

    cookie_key = f"{_LOGIN_COOKIE}_{token}"
    try:
        fails = int(request.cookies.get(cookie_key, "0"))
    except ValueError:
        fails = 0

    user_info = ldap_client.authenticate(username, password)

    if not user_info:
        fails += 1
        if fails >= _MAX_ATTEMPTS:
            response = templates.TemplateResponse(
                "contact_admin.html",
                {
                    "request": request,
                    "doc": doc,
                    "admin_email": settings.ADMIN_EMAIL,
                    "attempts": fails,
                    "reason": "login",
                },
            )
            response.delete_cookie(cookie_key)
            return response

        response = templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "doc": doc,
                "error": "invalid",
                "login_attempt": fails,
                "max_attempts": _MAX_ATTEMPTS,
            },
            status_code=401,
        )
        response.set_cookie(cookie_key, str(fails), httponly=True, samesite="lax", max_age=3600)
        return response

    response = RedirectResponse(f"/d/{token}", status_code=302)
    create_doc_session(response, token, user_info)
    response.delete_cookie(cookie_key)
    return response


# ---------------------------------------------------------------------------
# STEP 3a — confirm identity → open document (new attempt)
# ---------------------------------------------------------------------------
@router.post("/d/{token}/confirm", response_class=HTMLResponse)
async def confirm_identity(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    user = get_doc_session(request, token)
    if not user:
        return RedirectResponse(f"/d/{token}", status_code=302)

    log = log_service.create_attempt(
        db,
        document_id=doc.id,
        ad_username=user["username"],
        full_name=user.get("full_name"),
        department=user.get("department"),
        position=user.get("position"),
        email=user.get("email"),
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
    )

    response = templates.TemplateResponse(
        "viewer.html",
        {"request": request, "doc": doc, "user": user, "attempt_id": log.id, **TEMPLATE_CTX},
    )
    response.delete_cookie(f"{_DECLINE_COOKIE}_{token}")
    return response


# ---------------------------------------------------------------------------
# STEP 3b — decline identity → ask for AD login again (max attempts)
# ---------------------------------------------------------------------------
@router.post("/d/{token}/decline", response_class=HTMLResponse)
async def decline_identity(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    user = get_doc_session(request, token)
    if not user:
        return RedirectResponse(f"/d/{token}", status_code=302)

    cookie_key = f"{_DECLINE_COOKIE}_{token}"
    try:
        attempts = int(request.cookies.get(cookie_key, "0"))
    except ValueError:
        attempts = 0
    attempts += 1

    if attempts >= _MAX_ATTEMPTS:
        response = templates.TemplateResponse(
            "contact_admin.html",
            {
                "request": request,
                "doc": doc,
                "admin_email": settings.ADMIN_EMAIL,
                "attempts": attempts,
            },
        )
        response.delete_cookie(cookie_key)
        clear_doc_session(response, token)
        return response

    # Not "me" → clear session and ask for AD login again (each try re-authenticates)
    response = RedirectResponse(f"/d/{token}", status_code=302)
    clear_doc_session(response, token)
    response.set_cookie(cookie_key, str(attempts), httponly=True, samesite="lax", max_age=3600)
    return response


# ---------------------------------------------------------------------------
# STEP 4 — serve raw file
# ---------------------------------------------------------------------------
@router.get("/d/{token}/file")
async def serve_file(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    user = get_doc_session(request, token)
    if not user:
        raise HTTPException(403, "Authentication required")

    file_path = document_service.get_file_path(doc)
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")

    return FileResponse(
        path=str(file_path),
        media_type=doc.mime_type,
        filename=doc.original_filename,
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


# ---------------------------------------------------------------------------
# STEP 5 — acknowledge
# ---------------------------------------------------------------------------
@router.post("/d/{token}/acknowledge", response_class=HTMLResponse)
async def acknowledge(
    token: str,
    request: Request,
    attempt_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    doc = _get_doc_or_404(db, token)
    user = get_doc_session(request, token)
    if not user:
        raise HTTPException(403, "Authentication required")

    # Fallback to the user's most recent attempt if no id supplied (e.g. stale cache)
    if attempt_id is None:
        latest = log_service.latest_attempt(db, doc.id, user["username"])
        if not latest:
            raise HTTPException(400, "Attempt not found")
        attempt_id = latest.id

    log = log_service.acknowledge_attempt(db, attempt_id, user["username"])
    if not log:
        raise HTTPException(400, "Attempt not found")

    return templates.TemplateResponse(
        "final.html",
        {"request": request, "doc": doc, "user": user, "log": log},
    )
