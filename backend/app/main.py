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

app.include_router(doc_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.on_event("startup")
def on_startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()
    logging.getLogger(__name__).info(
        "Startup complete. DEV_MODE=%s DB=%s", settings.DEV_MODE, settings.DATABASE_URL
    )
