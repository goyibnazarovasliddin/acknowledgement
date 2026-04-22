"""
User-facing document flow endpoints.

GET  /d/{token}          — identify user, show confirm page
POST /d/{token}/confirm  — confirm identity → CONFIRMED
GET  /d/{token}/view     — document viewer (requires CONFIRMED or ACKNOWLEDGED)
GET  /d/{token}/file     — serve raw file (requires CONFIRMED or ACKNOWLEDGED)
POST /d/{token}/acknowledge — finalize → ACKNOWLEDGED
GET  /d/{token}/done     — final thank-you page
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "templates"

from app.auth.ldap_client import ldap_client
from app.auth.sso import get_remote_user
from app.config import settings
from app.database import get_db
from app.models import AckStatus, Document
from app.services import document_service, log_service

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

TEMPLATE_CTX = {
    "scroll_threshold": settings.SCROLL_THRESHOLD,
    "min_view_seconds": settings.MIN_VIEW_SECONDS,
}


def _get_doc_or_404(db: Session, token: str) -> Document:
    doc = document_service.get_by_token(db, token)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


# ---------------------------------------------------------------------------
# STEP 1 — open link
# ---------------------------------------------------------------------------
@router.get("/d/{token}", response_class=HTMLResponse)
async def open_document(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    remote_user = get_remote_user(request)

    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")

    if not remote_user:
        log_service.record_open(
            db,
            document_id=doc.id,
            ad_username=None,
            full_name=None,
            department=None,
            email=None,
            ip_address=ip,
            user_agent=ua,
        )
        return templates.TemplateResponse(
            "restricted.html",
            {"request": request, "doc": doc, **TEMPLATE_CTX},
        )

    # Fetch AD info
    user_info = ldap_client.get_user_info(remote_user)
    if not user_info:
        logger.warning("User %s authenticated but not found in LDAP", remote_user)
        user_info = {
            "username": remote_user,
            "full_name": remote_user,
            "department": "",
            "email": "",
        }

    log = log_service.record_open(
        db,
        document_id=doc.id,
        ad_username=user_info["username"],
        full_name=user_info["full_name"],
        department=user_info["department"],
        email=user_info["email"],
        ip_address=ip,
        user_agent=ua,
    )

    # Already confirmed / acknowledged → go straight to viewer
    if log.status in (AckStatus.CONFIRMED, AckStatus.ACKNOWLEDGED):
        return templates.TemplateResponse(
            "viewer.html",
            {"request": request, "doc": doc, "user": user_info, "log": log, **TEMPLATE_CTX},
        )

    return templates.TemplateResponse(
        "confirm.html",
        {"request": request, "doc": doc, "user": user_info, "log": log},
    )


# ---------------------------------------------------------------------------
# STEP 2b — decline identity (re-verify from AD, max 3 attempts)
# ---------------------------------------------------------------------------
_DECLINE_COOKIE = "ack_decline"
_MAX_ATTEMPTS   = settings.MAX_DECLINE_ATTEMPTS


@router.post("/d/{token}/decline", response_class=HTMLResponse)
async def decline_identity(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    remote_user = get_remote_user(request)

    if not remote_user:
        return templates.TemplateResponse("restricted.html", {"request": request, "doc": doc})

    # Read current attempt count from signed cookie
    cookie_key  = f"{_DECLINE_COOKIE}_{token}"
    raw_count   = request.cookies.get(cookie_key, "0")
    try:
        attempts = int(raw_count)
    except ValueError:
        attempts = 0

    attempts += 1

    if attempts >= _MAX_ATTEMPTS:
        # Blocked — show contact-admin page
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
        return response

    # Re-query AD for fresh data
    user_info = ldap_client.get_user_info(remote_user)
    if not user_info:
        user_info = {"username": remote_user, "full_name": remote_user, "department": "", "email": ""}

    response = templates.TemplateResponse(
        "confirm.html",
        {
            "request": request,
            "doc": doc,
            "user": user_info,
            "log": log_service.get_log(db, doc.id, user_info["username"]),
            "decline_attempt": attempts,
            "max_attempts": _MAX_ATTEMPTS,
        },
    )
    response.set_cookie(cookie_key, str(attempts), httponly=True, samesite="lax", max_age=3600)
    return response


# ---------------------------------------------------------------------------
# STEP 3 — confirm identity
# ---------------------------------------------------------------------------
@router.post("/d/{token}/confirm", response_class=HTMLResponse)
async def confirm_identity(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    remote_user = get_remote_user(request)

    if not remote_user:
        raise HTTPException(403, "SSO identity required")

    user_info = ldap_client.get_user_info(remote_user)
    if not user_info:
        user_info = {"username": remote_user, "full_name": remote_user, "department": "", "email": ""}

    log = log_service.get_log(db, doc.id, user_info["username"])
    if not log:
        raise HTTPException(400, "No open record found. Please reopen the link.")

    log = log_service.advance_to_confirmed(db, log)

    return templates.TemplateResponse(
        "viewer.html",
        {"request": request, "doc": doc, "user": user_info, "log": log, **TEMPLATE_CTX},
    )


# ---------------------------------------------------------------------------
# STEP 4 — serve raw file (viewer iframe / download)
# ---------------------------------------------------------------------------
@router.get("/d/{token}/file")
async def serve_file(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    remote_user = get_remote_user(request)

    if not remote_user:
        raise HTTPException(403, "Authentication required")

    user_info = ldap_client.get_user_info(remote_user)
    username = user_info["username"] if user_info else remote_user

    log = log_service.get_log(db, doc.id, username)
    if not log or log.status not in (AckStatus.CONFIRMED, AckStatus.ACKNOWLEDGED):
        raise HTTPException(403, "Identity confirmation required before accessing file")

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
async def acknowledge(token: str, request: Request, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, token)
    remote_user = get_remote_user(request)

    if not remote_user:
        raise HTTPException(403, "SSO identity required")

    user_info = ldap_client.get_user_info(remote_user)
    username = user_info["username"] if user_info else remote_user

    log = log_service.get_log(db, doc.id, username)
    if not log or log.status not in (AckStatus.CONFIRMED, AckStatus.ACKNOWLEDGED):
        raise HTTPException(400, "Cannot acknowledge before confirming identity")

    log = log_service.advance_to_acknowledged(db, log)

    return templates.TemplateResponse(
        "final.html",
        {"request": request, "doc": doc, "user": user_info or {}, "log": log},
    )
