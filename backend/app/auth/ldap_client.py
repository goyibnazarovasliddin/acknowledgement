import logging
from typing import Optional

from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError

from app.config import settings

logger = logging.getLogger(__name__)

_ATTRIBUTES = ["displayName", "department", "mail", "sAMAccountName"]


class LDAPClient:
    def __init__(self):
        self._server = Server(settings.LDAP_SERVER, get_info=ALL, connect_timeout=5)

    def _connect(self) -> Connection:
        conn = Connection(
            self._server,
            user=settings.LDAP_BIND_DN,
            password=settings.LDAP_PASSWORD,
            authentication=SIMPLE,
            auto_bind=True,
            raise_exceptions=True,
        )
        return conn

    def get_user_info(self, raw_username: str) -> Optional[dict]:
        """
        Accepts DOMAIN\\username or bare username.
        Returns dict with username/full_name/department/email, or None if not found.
        """
        sam = self._extract_sam(raw_username)
        if not sam:
            return None

        try:
            conn = self._connect()
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
                "email": self._str(entry, "mail") or "",
            }

        except LDAPBindError as exc:
            logger.error("LDAP bind failed: %s", exc)
            return None
        except LDAPException as exc:
            logger.error("LDAP error for %s: %s", sam, exc)
            return None

    @staticmethod
    def _extract_sam(raw: str) -> str:
        """Strip DOMAIN\\ prefix or UPN suffix."""
        if "\\" in raw:
            return raw.split("\\", 1)[1]
        if "@" in raw:
            return raw.split("@", 1)[0]
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
