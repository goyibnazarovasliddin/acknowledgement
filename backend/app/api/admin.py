"""
Admin panel — session-auth protected.

GET/POST /admin/login
GET      /admin/logout
GET      /admin/
GET/POST /admin/upload
GET      /admin/documents/{id}
GET      /admin/documents/{id}/logs.json
GET      /admin/documents/{id}/users/{username}
GET      /admin/documents/{id}/users/{username}/logs.json
GET      /admin/documents/{id}/export/csv|excel
DELETE   /admin/documents/{id}
"""
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.ldap_client import ldap_client
from app.auth.session import clear_session, create_session, get_session_user
from app.config import settings
from app.security import login_blocked, record_login_failure, reset_login, verify_admin
from app.database import get_db
from app.models import AckStatus, Document, DocumentLog
from app.services import document_service, export_service, log_service
from app.services.document_service import list_documents
from app.timeutil import fmt_local

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "templates"

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.filters["localdt"] = fmt_local


def _require_admin(request: Request) -> str:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return user


def _fmt(dt) -> str:
    return fmt_local(dt)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if get_session_user(request):
        return RedirectResponse("/admin/", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


def _login_ip(request: Request) -> str:
    # Trust only the proxy-set X-Real-IP (nginx sets it to the real client);
    # fall back to the socket peer. Never the client-spoofable X-Forwarded-For.
    return request.headers.get("X-Real-IP") or (request.client.host if request.client else "")


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = _login_ip(request)
    if login_blocked(ip):
        logger.warning("Admin login locked out for %s (too many failures)", ip)
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Juda ko'p urinish. Birozdan so'ng qayta urining."},
            status_code=429,
        )

    if verify_admin(username, password):
        reset_login(ip)
        response = RedirectResponse("/admin/", status_code=302)
        create_session(response, settings.ADMIN_USERNAME)
        return response

    record_login_failure(ip)
    logger.warning("Admin login failed for %r from %s", username, ip)
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": "Login yoki parol noto'g'ri"},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    clear_session(response)
    return response


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    docs = list_documents(db)
    doc_stats = []
    for doc in docs:
        # distinct users who acknowledged
        ack_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.status == AckStatus.ACKNOWLEDGED)
            .distinct()
            .count()
        )
        total_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id)
            .distinct()
            .count()
        )
        doc_stats.append({"doc": doc, "ack_count": ack_users, "total_count": total_users})

    # ---- KPI aggregates ----
    dir_stats = ldap_client.get_directory_stats()
    total_ad_users = dir_stats["total_users"]
    total_ad_depts = len(dir_stats["departments"])

    # Only non-archived documents feed the KPI cards and charts.
    active_ids = db.query(Document.id).filter(Document.archived == False)

    total_docs = len(docs)
    system_users = (
        db.query(DocumentLog.ad_username)
        .filter(DocumentLog.document_id.in_(active_ids))
        .distinct()
        .count()
    )
    ack_users = (
        db.query(DocumentLog.ad_username)
        .filter(DocumentLog.status == AckStatus.ACKNOWLEDGED, DocumentLog.document_id.in_(active_ids))
        .distinct()
        .count()
    )
    coverage = round(system_users / total_ad_users * 100) if total_ad_users else 0

    stats = {
        "total_docs": total_docs,
        "total_ad_users": total_ad_users,
        "total_ad_depts": total_ad_depts,
        "system_users": system_users,
        "ack_users": ack_users,
        "coverage": coverage,
    }

    # ---- Chart data ----
    # Donut: acknowledged vs not (relative to AD total)
    not_ack = max(total_ad_users - ack_users, 0)

    # Bar: distinct acknowledged users per department (from our records)
    pairs = (
        db.query(DocumentLog.department, DocumentLog.ad_username)
        .filter(DocumentLog.status == AckStatus.ACKNOWLEDGED, DocumentLog.document_id.in_(active_ids))
        .distinct()
        .all()
    )
    dept_counter = Counter((d or "—") for d, _ in pairs)
    dept_top = dept_counter.most_common(10)

    # Line: acknowledgements per local day, last 30 days
    offset = timedelta(hours=settings.TZ_OFFSET_HOURS)
    since_utc = datetime.utcnow() - timedelta(days=30)
    ack_rows = (
        db.query(DocumentLog.acknowledged_at)
        .filter(
            DocumentLog.status == AckStatus.ACKNOWLEDGED,
            DocumentLog.acknowledged_at >= since_utc,
            DocumentLog.document_id.in_(active_ids),
        )
        .all()
    )
    day_counter = Counter()
    for (dt,) in ack_rows:
        if dt:
            day_counter[(dt + offset).strftime("%Y-%m-%d")] += 1
    today_local = (datetime.utcnow() + offset).date()
    day_labels, day_data = [], []
    for i in range(29, -1, -1):
        d = (today_local - timedelta(days=i)).strftime("%Y-%m-%d")
        day_labels.append(d[5:])  # MM-DD
        day_data.append(day_counter.get(d, 0))

    charts = {
        "donut": {"ack": ack_users, "not_ack": not_ack},
        "dept": {"labels": [d for d, _ in dept_top], "data": [c for _, c in dept_top]},
        "daily": {"labels": day_labels, "data": day_data},
    }

    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "doc_stats": doc_stats,
            "stats": stats,
            "charts": charts,
            "admin_user": admin_user,
        },
    )


@router.get("/dashboard/stats.json")
async def dashboard_stats_json(request: Request, db: Session = Depends(get_db)):
    """Live counts for the dashboard table + KPI cards (polled by index.html)."""
    _require_admin(request)
    docs = list_documents(db)
    doc_rows = []
    for doc in docs:
        ack = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.status == AckStatus.ACKNOWLEDGED)
            .distinct().count()
        )
        total = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id)
            .distinct().count()
        )
        doc_rows.append({"id": doc.id, "ack_count": ack, "total_count": total})

    active_ids = db.query(Document.id).filter(Document.archived == False)
    system_users = (
        db.query(DocumentLog.ad_username)
        .filter(DocumentLog.document_id.in_(active_ids))
        .distinct().count()
    )
    ack_users = (
        db.query(DocumentLog.ad_username)
        .filter(DocumentLog.status == AckStatus.ACKNOWLEDGED, DocumentLog.document_id.in_(active_ids))
        .distinct().count()
    )
    total_ad_users = ldap_client.get_directory_stats()["total_users"]
    coverage = round(system_users / total_ad_users * 100) if total_ad_users else 0
    return {
        "docs": doc_rows,
        "stats": {"system_users": system_users, "ack_users": ack_users, "coverage": coverage},
    }


# ---------------------------------------------------------------------------
# Archive (soft-archived documents) — same flow as dashboard
# ---------------------------------------------------------------------------
@router.get("/archive", response_class=HTMLResponse)
async def admin_archive(request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    docs = list_documents(db, archived=True)
    doc_stats = []
    for doc in docs:
        ack_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.status == AckStatus.ACKNOWLEDGED)
            .distinct()
            .count()
        )
        total_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id)
            .distinct()
            .count()
        )
        doc_stats.append({"doc": doc, "ack_count": ack_users, "total_count": total_users})

    return templates.TemplateResponse(
        "admin/archive.html",
        {"request": request, "doc_stats": doc_stats, "admin_user": admin_user},
    )


@router.post("/documents/{doc_id}/archive")
async def archive_document(doc_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    document_service.archive_document(db, doc)
    return {"ok": True}


@router.post("/documents/{doc_id}/unarchive")
async def unarchive_document(doc_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    document_service.unarchive_document(db, doc)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    admin_user = _require_admin(request)
    return templates.TemplateResponse("admin/upload.html", {"request": request, "admin_user": admin_user})


@router.post("/upload", response_class=HTMLResponse)
async def upload_document(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    admin_user = _require_admin(request)
    doc = await document_service.save_document(db, file, title, uploaded_by=admin_user)
    return templates.TemplateResponse(
        "admin/upload_success.html",
        {"request": request, "doc": doc, "admin_user": admin_user},
    )


# ---------------------------------------------------------------------------
# Document detail — grouped per user
# ---------------------------------------------------------------------------
def _apply_filters(rows, status, department):
    if status:
        rows = [r for r in rows if r["status"].value == status]
    if department:
        d = department.lower()
        rows = [r for r in rows if (r.get("department") or "").lower().find(d) >= 0]
    return rows


def _detail_response(request, db, doc_id, status, department, section, admin_user):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    all_rows = log_service.list_user_rows(db, doc_id)
    rows = _apply_filters(all_rows, status, department)
    departments = sorted({r["department"] for r in all_rows if r.get("department")})
    return templates.TemplateResponse(
        "admin/document_detail.html",
        {
            "request": request,
            "doc": doc,
            "rows": rows,
            "ack_statuses": list(AckStatus),
            "departments": departments,
            "filter_status": status,
            "filter_department": department,
            "admin_user": admin_user,
            "section": section,
        },
    )


@router.get("/documents/{doc_id}", response_class=HTMLResponse)
async def document_detail(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    admin_user = _require_admin(request)
    return _detail_response(request, db, doc_id, status, department, "documents", admin_user)


@router.get("/archive/documents/{doc_id}", response_class=HTMLResponse)
async def archive_document_detail(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    admin_user = _require_admin(request)
    return _detail_response(request, db, doc_id, status, department, "archive", admin_user)


@router.get("/documents/{doc_id}/logs.json")
async def document_logs_json(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    rows = _apply_filters(log_service.list_user_rows(db, doc_id), status, department)
    return {
        "rows": [
            {
                "username": r["username"],
                "full_name": r["full_name"] or "",
                "department": r["department"] or "",
                "position": r["position"] or "",
                "status": r["status"].value,
                "time": _fmt(r["time"]),
                "ip_address": r["ip_address"] or "",
                "attempts": r["attempts"],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# User drill-down — all attempts of one user for this document
# ---------------------------------------------------------------------------
def _user_response(request, db, doc_id, username, section, admin_user):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    attempts = log_service.list_attempts(db, doc_id, username)
    return templates.TemplateResponse(
        "admin/user_attempts.html",
        {
            "request": request,
            "doc": doc,
            "username": username,
            "attempts": attempts,
            "admin_user": admin_user,
            "section": section,
        },
    )


@router.get("/documents/{doc_id}/users/{username}", response_class=HTMLResponse)
async def user_attempts(doc_id: int, username: str, request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    return _user_response(request, db, doc_id, username, "documents", admin_user)


@router.get("/archive/documents/{doc_id}/users/{username}", response_class=HTMLResponse)
async def archive_user_attempts(doc_id: int, username: str, request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    return _user_response(request, db, doc_id, username, "archive", admin_user)


@router.get("/documents/{doc_id}/users/{username}/logs.json")
async def user_attempts_json(doc_id: int, username: str, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    attempts = log_service.list_attempts(db, doc_id, username)
    return {
        "rows": [
            {
                "status": a.status.value,
                "opened_at": _fmt(a.opened_at),
                "acknowledged_at": _fmt(a.acknowledged_at),
                "time": _fmt(a.acknowledged_at or a.opened_at),
                "ip_address": a.ip_address or "",
            }
            for a in attempts
        ]
    }


# ---------------------------------------------------------------------------
# Exports — raw attempts
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}/export/csv")
async def export_csv(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    data = export_service.export_csv(_filtered_logs(db, doc_id, status, department))
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ack_{doc_id}.csv"'},
    )


@router.get("/documents/{doc_id}/export/excel")
async def export_excel(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    data = export_service.export_excel(_filtered_logs(db, doc_id, status, department), doc.title)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="ack_{doc_id}.xlsx"'},
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    document_service.delete_document(db, doc, deleted_by=admin_user)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin file view/download
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}/file")
async def admin_serve_file(doc_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    file_path = document_service.get_file_path(doc)
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    disposition = "inline" if doc.mime_type == "application/pdf" else "attachment"
    return FileResponse(
        path=str(file_path),
        media_type=doc.mime_type,
        filename=doc.original_filename,
        headers={
            "Content-Disposition": f'{disposition}; filename="{doc.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filtered_logs(db: Session, doc_id: int, status: str | None, department: str | None):
    query = db.query(DocumentLog).filter(DocumentLog.document_id == doc_id)
    if status:
        try:
            query = query.filter(DocumentLog.status == AckStatus(status))
        except ValueError:
            pass
    if department:
        query = query.filter(DocumentLog.department.ilike(f"%{department}%"))
    return query.order_by(DocumentLog.opened_at.desc()).all()
