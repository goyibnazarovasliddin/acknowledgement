import logging
import time
from typing import Optional

from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError

from app.config import settings

logger = logging.getLogger(__name__)

_ATTRIBUTES = ["displayName", "department", "title", "mail", "sAMAccountName"]

# Active (non-disabled) person accounts. The bit-AND rule filters out disabled.
_ALL_USERS_FILTER = (
    "(&(objectCategory=person)(objectClass=user)"
    "(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
)

_DIR_CACHE: dict = {}
_DIR_CACHE_TTL = 1800  # 30 min — AD-wide scan is heavy, cache it


class LDAPClient:
    def __init__(self):
        self._server = Server(settings.LDAP_SERVER, get_info=ALL, connect_timeout=5)

    def _service_connect(self) -> Connection:
        """Bind with the service account (for attribute lookups)."""
        return Connection(
            self._server,
            user=settings.LDAP_BIND_DN,
            password=settings.LDAP_PASSWORD,
            authentication=SIMPLE,
            auto_bind=True,
            raise_exceptions=True,
        )

    # ------------------------------------------------------------------
    # User authentication — bind with the user's OWN credentials
    # ------------------------------------------------------------------
    def authenticate(self, raw_username: str, password: str) -> Optional[dict]:
        """
        Verify user credentials against AD by binding as the user.
        Returns user_info dict on success, None on failure.

        DEV_MODE: any username + DEV_LOGIN_PASSWORD returns a synthetic
        identity so the flow can be tested without a real AD.
        """
        sam = self._extract_sam(raw_username)
        if not sam or not password:
            return None

        if settings.DEV_MODE:
            if password == settings.DEV_LOGIN_PASSWORD:
                return {
                    "username": sam,
                    "full_name": sam.replace(".", " ").title(),
                    "department": "Test bo'lim",
                    "position": "Test lavozim",
                    "email": f"{sam}@{settings.LDAP_DOMAIN}",
                }
            logger.warning("DEV auth failed for %s (wrong dev password)", sam)
            return None

        upn = f"{sam}@{settings.LDAP_DOMAIN}"
        try:
            conn = Connection(
                self._server,
                user=upn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
                raise_exceptions=True,
            )
        except LDAPBindError:
            logger.info("LDAP auth rejected for %s", upn)
            return None
        except LDAPException as exc:
            logger.error("LDAP auth error for %s: %s", upn, exc)
            return None

        # Bind OK → fetch attributes (reuse the authenticated connection)
        info = self._search(conn, sam)
        try:
            conn.unbind()
        except LDAPException:
            pass

        if info:
            return info
        # Authenticated but no directory entry found — return minimal identity
        return {
            "username": sam,
            "full_name": sam,
            "department": "",
            "position": "",
            "email": "",
        }

    def get_user_info(self, raw_username: str) -> Optional[dict]:
        """Lookup attributes via the service account (no password check)."""
        sam = self._extract_sam(raw_username)
        if not sam:
            return None
        if settings.DEV_MODE:
            return {
                "username": sam,
                "full_name": sam.replace(".", " ").title(),
                "department": "Test bo'lim",
                "position": "Test lavozim",
                "email": f"{sam}@{settings.LDAP_DOMAIN}",
            }
        try:
            conn = self._service_connect()
            info = self._search(conn, sam)
            conn.unbind()
            return info
        except LDAPBindError as exc:
            logger.error("LDAP bind failed: %s", exc)
            return None
        except LDAPException as exc:
            logger.error("LDAP error for %s: %s", sam, exc)
            return None

    # ------------------------------------------------------------------
    # Directory-wide stats (total users, departments) — cached
    # ------------------------------------------------------------------
    def get_directory_stats(self) -> dict:
        now = time.time()
        cached = _DIR_CACHE.get("dir")
        if cached and now - cached[0] < _DIR_CACHE_TTL:
            return cached[1]
        data = self._fetch_directory_stats()
        _DIR_CACHE["dir"] = (now, data)
        return data

    def _fetch_directory_stats(self) -> dict:
        if settings.DEV_MODE:
            return {
                "total_users": 250,
                "departments": [
                    "Buxgalteriya", "Axborot texnologiyalari", "Kadrlar bo'limi",
                    "Yuridik departament", "Operatsion boshqarma", "Xavfsizlik xizmati",
                ],
            }
        try:
            conn = self._service_connect()
            entries = conn.extend.standard.paged_search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=_ALL_USERS_FILTER,
                search_scope=SUBTREE,
                attributes=["department"],
                paged_size=500,
                generator=True,
            )
            total = 0
            depts = set()
            for e in entries:
                if e.get("type") != "searchResEntry":
                    continue
                total += 1
                d = e["attributes"].get("department")
                if isinstance(d, list):
                    d = d[0] if d else None
                if d:
                    depts.add(str(d))
            conn.unbind()
            return {"total_users": total, "departments": sorted(depts)}
        except LDAPException as exc:
            logger.error("LDAP directory stats failed: %s", exc)
            return {"total_users": 0, "departments": []}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _search(self, conn: Connection, sam: str) -> Optional[dict]:
        conn.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=f"(sAMAccountName={self._escape_filter(sam)})",
            search_scope=SUBTREE,
            attributes=_ATTRIBUTES,
        )
        if not conn.entries:
            logger.warning("LDAP: no entry for sAMAccountName=%s", sam)
            return None
        entry = conn.entries[0]
        return {
            "username": str(entry.sAMAccountName),
            "full_name": self._str(entry, "displayName") or sam,
            "department": self._str(entry, "department") or "",
            "position": self._str(entry, "title") or "",
            "email": self._str(entry, "mail") or "",
        }

    @staticmethod
    def _extract_sam(raw: str) -> str:
        """Strip DOMAIN\\ prefix or UPN suffix."""
        if not raw:
            return ""
        if "\\" in raw:
            return raw.split("\\", 1)[1].strip()
        if "@" in raw:
            return raw.split("@", 1)[0].strip()
        return raw.strip()

    @staticmethod
    def _str(entry, attr: str) -> str:
        val = getattr(entry, attr, None)
        if val is None:
            return ""
        s = str(val)
        return "" if s == "[]" else s

    @staticmethod
    def _escape_filter(value: str) -> str:
        """Minimal LDAP filter escaping (RFC 4515)."""
        return (
            value
            .replace("\\", "\\5c")
            .replace("*", "\\2a")
            .replace("(", "\\28")
            .replace(")", "\\29")
            .replace("\x00", "\\00")
        )


ldap_client = LDAPClient()
