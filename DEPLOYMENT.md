# Deployment Guide

> 🇺🇿 [O'zbekcha](DEPLOYMENT.uz.md) &nbsp;|&nbsp; 🇬🇧 English

Production deploy: Docker + PostgreSQL + Active Directory LDAP.

## How authentication works

Employees open a document link → the app reads the `REMOTE_USER` HTTP header to identify them. **This header must be set by an upstream authentication proxy (IIS or Apache) that performs Kerberos/NTLM authentication against Active Directory.**

```
Browser → IIS or Apache (Kerberos/NTLM → sets REMOTE_USER) → Nginx → App → AD LDAP lookup
```

Without this proxy in front, employees will see "Kirish cheklangan" (access restricted). The admin panel (`/admin`) does NOT require SSO — it uses its own username/password login.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker | 24+ |
| Docker Compose | v2 (`docker compose`) |
| OS | Ubuntu 22.04 / Debian 12 / RHEL 8+ |
| RAM | 2 GB minimum |
| Disk | 20 GB minimum |
| Network | Server must reach AD on TCP/389 |

Install Docker if not present:
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/goyibnazarovasliddin/acknowledgement.git
cd acknowledgement
```

---

## Step 2 — Create `.env`

```bash
cp .env.example .env
nano .env
```

Fill in **all** required values:

```env
# PostgreSQL
POSTGRES_USER=ack_user
POSTGRES_PASSWORD=<strong password>
POSTGRES_DB=acknowledgement

# Active Directory
LDAP_SERVER=<AD server IP>
LDAP_BIND_DN=CN=training,OU=Services Users,OU=Priveleged Accounts,DC=corp,DC=agrobank,DC=uz
LDAP_PASSWORD=<service account password>
LDAP_BASE_DN=DC=corp,DC=agrobank,DC=uz

# Generate SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<32+ char random string>

# Admin panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong password>
ADMIN_EMAIL=<your email>
```

> **Warning:** Never commit `.env` to git. It is already listed in `.gitignore`.

---

## Step 3 — SSL Certificate

**Option A — Self-signed** (internal network):
```bash
mkdir -p certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -subj "/CN=ack.corp.agrobank.uz/O=Agrobank/C=UZ"
```

**Option B — Existing corporate certificate:**
```bash
mkdir -p certs
cp /path/to/your/fullchain.pem certs/fullchain.pem
cp /path/to/your/privkey.pem   certs/privkey.pem
```

---

## Step 4 — Verify AD connectivity

```bash
nc -zv <LDAP_SERVER IP> 389
# Expected: Connection to <IP> 389 port [tcp/ldap] succeeded!
```

If port 389 is blocked → ask your network admin to allow `TCP/389` from this server to the AD host.

---

## Step 5 — Build and start

```bash
docker compose up -d --build
```

```bash
docker compose ps
# All three containers must be Up: app, db, nginx
```

---

## Step 6 — Verify

```bash
# Admin panel reachable:
curl -k https://localhost/admin/login

# LDAP connection test from inside container:
docker compose exec app python3 -c "
from app.auth.ldap_client import ldap_client
print(ldap_client.get_user_info('firstname.lastname'))
"
```

---

## Step 7 — Configure SSO proxy (required for employees)

Choose **one** option based on your environment.

---

### Option A — Windows Server (IIS)

Use this if the server running Docker is Windows, or if you have a separate Windows Server available as a front-end proxy.

**Requirements:** Windows Server with IIS + `Application Request Routing (ARR)` + `Windows Authentication` modules installed.

**1. Install IIS modules:**
- Open *Server Manager → Add Roles and Features*
- Add: `Web Server (IIS)` → `Security` → `Windows Authentication`
- Download and install [Application Request Routing (ARR)](https://www.iis.net/downloads/microsoft/application-request-routing)

**2. Create a new IIS site:**
- Binding: HTTPS port 443 (or 80)
- Physical path: any empty folder

**3. Enable Windows Authentication:**
- Select the site → *Authentication*
- Disable `Anonymous Authentication`
- Enable `Windows Authentication`

**4. Configure reverse proxy to Docker app (`web.config`):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Proxy to Docker" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://localhost:8080/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <security>
      <authentication>
        <anonymousAuthentication enabled="false" />
        <windowsAuthentication enabled="true" />
      </authentication>
    </security>
  </system.webServer>
</configuration>
```

> IIS sets `REMOTE_USER` header automatically as `DOMAIN\username` after Windows Authentication succeeds. The app strips the `DOMAIN\` prefix internally.

**5. Update `docker-compose.yml` nginx ports** (IIS now handles SSL):
```yaml
ports:
  - "127.0.0.1:8080:80"
```

---

### Option B — Linux Server (Apache + mod_auth_kerb)

Use this if the server is Linux and your AD has Kerberos configured.

**1. Install Apache and Kerberos module:**
```bash
apt install apache2 libapache2-mod-auth-kerb krb5-user -y
a2enmod auth_kerb proxy proxy_http headers ssl
```

**2. Get a Kerberos keytab** from your AD admin for `HTTP/hostname@REALM`.

**3. Create Apache virtual host** `/etc/apache2/sites-available/ack.conf`:
```apache
<VirtualHost *:443>
    ServerName ack.corp.agrobank.uz

    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/fullchain.pem
    SSLCertificateKeyFile /etc/ssl/private/privkey.pem

    <Location />
        AuthType Kerberos
        AuthName "Agrobank Corporate Login"
        KrbAuthRealms CORP.AGROBANK.UZ
        KrbServiceName HTTP
        Krb5Keytab /etc/apache2/http.keytab
        KrbMethodNegotiate On
        KrbMethodK5Passwd Off
        Require valid-user

        RequestHeader set REMOTE_USER "%{REMOTE_USER}s"
    </Location>

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/
</VirtualHost>
```

**4. Enable site and restart:**
```bash
a2ensite ack
systemctl restart apache2
```

**5. Update `docker-compose.yml` nginx ports:**
```yaml
ports:
  - "127.0.0.1:8080:80"
```

---

### Option C — Linux Server (Apache + NTLM)

Use this if Kerberos is not configured but NTLM works. Requires `libapache2-mod-auth-ntlm-winbind` and Winbind joined to the domain. Contact your AD admin for domain join — Apache config is identical to Option B but with `AuthType NTLM`.

---

## Architecture after SSO setup

```
Employee browser
      │
      ▼
IIS (Windows Auth) or Apache (mod_auth_kerb)
  → authenticates via Kerberos/NTLM against AD
  → sets header: REMOTE_USER: CORP\firstname.lastname
      │
      ▼
Nginx (Docker, port 8080 internal)
  → forwards REMOTE_USER header
      │
      ▼
FastAPI app
  → reads REMOTE_USER
  → looks up user details in AD via LDAP
  → shows document to confirmed user
```

---

## Environment variables reference

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | Yes | PostgreSQL database name |
| `LDAP_SERVER` | Yes | Active Directory server IP |
| `LDAP_BIND_DN` | Yes | Service account full DN |
| `LDAP_PASSWORD` | Yes | Service account password |
| `LDAP_BASE_DN` | Yes | AD search base |
| `SECRET_KEY` | Yes | Cookie signing key (min 32 chars) |
| `ADMIN_USERNAME` | Yes | Admin panel username |
| `ADMIN_PASSWORD` | Yes | Admin panel password |
| `ADMIN_EMAIL` | Yes | Shown to users when blocked |
| `ADMIN_SESSION_HOURS` | No | Session duration (default: 8) |
| `MAX_FILE_SIZE_MB` | No | Upload limit (default: 100) |
| `MAX_DECLINE_ATTEMPTS` | No | Identity decline limit (default: 3) |
| `SCROLL_THRESHOLD` | No | Scroll % required (default: 0.90) |
| `MIN_VIEW_SECONDS` | No | Min read time in seconds (default: 20) |

---

## Useful commands

```bash
# Stop
docker compose down

# Stop and delete all data (DB + uploads)
docker compose down -v

# View logs
docker compose logs -f app

# Restart app only
docker compose restart app

# Update after git pull
git pull
docker compose up -d --build
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `502 Bad Gateway` | App container not ready | Wait 10s, check `docker compose logs app` |
| `LDAP bind failed` | Wrong password or DN | Check `LDAP_PASSWORD` and `LDAP_BIND_DN` in `.env` |
| `Connection refused :389` | Firewall blocking LDAP | Allow TCP/389 from server to AD host |
| `SSL handshake error` | Missing certs | Run Step 3 again |
| `db not healthy` | Wrong `POSTGRES_*` vars | Check `.env`, run `docker compose down -v` then restart |
| Admin login fails | Wrong `ADMIN_PASSWORD` | Check `.env`, restart: `docker compose restart app` |
| Employees see "Kirish cheklangan" | `REMOTE_USER` header missing | Configure IIS or Apache SSO proxy (Step 7) |
| Kerberos auth fails | Keytab expired or wrong realm | Get new keytab from AD admin |
