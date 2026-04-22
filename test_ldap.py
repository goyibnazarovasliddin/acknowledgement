"""
Standalone LDAP/AD connection test.
Fill in the variables below and run:
    python test_ldap.py
Does NOT affect the project — no imports from app code.
"""

# ── Fill these in ──────────────────────────────────────────
LDAP_SERVER   = "X.X.X.X"  # IP or hostname of your LDAP/AD server
LDAP_BIND_DN  = "CN=xx,OU=xx xx,OU=xx xx,DC=xx,DC=xx,DC=xx"
LDAP_PASSWORD = "PASSWORD_FOR_BIND_DN"
LDAP_BASE_DN  = "DC=xx,DC=xx,DC=xx"
TEST_USERNAME = "a.goyibnazarov"   # sAMAccountName — test qilmoqchi bo'lgan user
# ───────────────────────────────────────────────────────────

from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError

def test_bind():
    print(f"\n[1] Connecting to {LDAP_SERVER}:389 ...")
    try:
        server = Server(LDAP_SERVER, get_info=ALL, connect_timeout=5)
        conn = Connection(
            server,
            user=LDAP_BIND_DN,
            password=LDAP_PASSWORD,
            authentication=SIMPLE,
            auto_bind=True,
            raise_exceptions=True,
        )
        print(f"    OK — bind successful")
        print(f"    Server info: {server.info.vendor_name if server.info else 'n/a'}")
        return conn
    except LDAPBindError as e:
        print(f"    FAIL — bind error: {e}")
        print("    Check: LDAP_BIND_DN and LDAP_PASSWORD")
        return None
    except LDAPException as e:
        print(f"    FAIL — connection error: {e}")
        print("    Check: LDAP_SERVER IP and TCP/389 port open")
        return None
    except Exception as e:
        print(f"    FAIL — {e}")
        return None

def test_search(conn):
    print(f"\n[2] Searching for user sAMAccountName={TEST_USERNAME} ...")
    try:
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(sAMAccountName={TEST_USERNAME})",
            search_scope=SUBTREE,
            attributes=["displayName", "department", "mail", "sAMAccountName"],
        )
        if not conn.entries:
            print(f"    NOT FOUND — user '{TEST_USERNAME}' does not exist in AD")
            print("    Check: TEST_USERNAME correct? LDAP_BASE_DN correct?")
            return
        entry = conn.entries[0]
        print(f"    OK — user found:")
        print(f"      sAMAccountName : {entry.sAMAccountName}")
        print(f"      displayName    : {entry.displayName}")
        print(f"      department     : {entry.department}")
        print(f"      mail           : {entry.mail}")
    except LDAPException as e:
        print(f"    FAIL — search error: {e}")

def test_port():
    import socket
    print(f"\n[0] TCP port check {LDAP_SERVER}:389 ...")
    try:
        s = socket.create_connection((LDAP_SERVER, 389), timeout=5)
        s.close()
        print(f"    OK — port 389 reachable")
        return True
    except Exception as e:
        print(f"    FAIL — {e}")
        print("    TCP/389 blocked. Ask network admin to open it.")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("AD / LDAP Connection Test")
    print("=" * 50)

    if not test_port():
        exit(1)

    conn = test_bind()
    if not conn:
        exit(1)

    test_search(conn)

    print("\nDone.")
