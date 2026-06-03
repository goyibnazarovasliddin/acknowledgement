import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.api.documents import router as doc_router
from app.api.admin import router as admin_router
from app.config import settings
from app.security import CONTENT_SECURITY_POLICY, check_dev_mode, validate_production_settings

# backend/app/main.py → backend/ → repo root → frontend/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Document Acknowledgement System",
    description="Employee acknowledgement tracking for internal documents",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEV_MODE else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
    """Add hardening headers to every response (clickjacking, MIME-sniffing,
    referrer leakage, CSP). HSTS only in production (TLS terminated at nginx)."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if not settings.DEV_MODE:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def no_cache_static(request, call_next):
    """Always revalidate static assets so updated JS/CSS reach users after a
    redeploy (no stale cache), in both dev and production."""
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.include_router(doc_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.on_event("startup")
def on_startup():
    log = logging.getLogger(__name__)
    dev_fatal, dev_warn = check_dev_mode()
    for w in dev_warn:
        log.warning(w)
    problems = validate_production_settings() + dev_fatal
    if problems:
        msg = "Insecure configuration:\n  - " + "\n  - ".join(problems)
        log.critical(msg)
        raise RuntimeError(msg)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()
    logging.getLogger(__name__).info(
        "Startup complete. DEV_MODE=%s DB=%s", settings.DEV_MODE, settings.DATABASE_URL
    )
