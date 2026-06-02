from pathlib import Path
from pydantic_settings import BaseSettings

# repo_root/backend/app/config.py → repo_root/backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{_BACKEND_DIR / 'acknowledgement.db'}"

    LDAP_SERVER: str = "SERVER_IP"
    LDAP_BIND_DN: str = "CN=training,OU=Services Users,OU=Priveleged Accounts,DC=corp,DC=agrobank,DC=uz"
    LDAP_PASSWORD: str = "PASSWORD"
    LDAP_BASE_DN: str = "DC=corp,DC=agrobank,DC=uz"
    LDAP_DOMAIN: str = "corp.agrobank.uz"  # UPN suffix for user bind (sam@DOMAIN)

    # DEV_MODE only: lets any username log in with this password (no real AD).
    DEV_LOGIN_PASSWORD: str = "dev"

    SECRET_KEY: str = "change-me-in-production"
    UPLOAD_DIR: str = str(_BACKEND_DIR / "uploads")
    MAX_FILE_SIZE_MB: int = 100

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_SESSION_HOURS: int = 8
    ADMIN_EMAIL: str = "goyibnazarovasliddin@gmail.com"

    MAX_DECLINE_ATTEMPTS: int = 3

    SCROLL_THRESHOLD: float = 0.90
    MIN_VIEW_SECONDS: int = 20

    DEV_MODE: bool = False

    # Display timezone offset from UTC (Asia/Tashkent & Ashgabat = +5, no DST).
    # DB stores UTC; times are converted to this offset for display/export.
    TZ_OFFSET_HOURS: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
