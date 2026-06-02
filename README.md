# Document Acknowledgement System

> 🇺🇿 [O'zbekcha](README.uz.md) &nbsp;|&nbsp; 🇬🇧 English

Internal document acknowledgement tracking for Agrobank employees.

Employees open a unique link, sign in with their own Active Directory credentials, confirm the identity shown, read the document, and acknowledge it. Admins track, in real time, who has and hasn't acknowledged.

## Features

- **AD login** — users authenticate with their own AD username + password (LDAP bind). No SSO/Kerberos required.
- **Identity confirmation** — after login the system shows the user's full name, department and position ("Is this you?"). Declining re-asks for login; after 3 failed identity/login attempts the user is told to contact the admin.
- **Document viewer** — PDF rendered inline with scroll (≥ threshold) + minimum-time enforcement before "Acknowledge" unlocks. Scroll requirement applies to PDFs only.
- **Attempt-based reporting** — every open is a separate attempt. The per-document table shows one row per user (their first attempt); clicking a user drills down to all their attempts. Updates in real time.
- **Admin analytics** — KPI cards (AD total users, departments, coverage %) and charts (acknowledged vs not, by department, last-30-day trend).
- **Archive + deep archive** — documents can be archived (hidden, data preserved) and restored. Deleting from the archive moves a full snapshot into a hidden `deep_archive` table so nothing is lost at the DB level.
- **Export** — CSV / Excel (openpyxl), per document.
- **i18n** — Uzbek / Russian (client-side). All times shown in a fixed display timezone (Tashkent/Ashgabat, UTC+5).

## Architecture

```
Browser → Nginx (SSL) → FastAPI → PostgreSQL
                            ↓
                Active Directory (LDAP bind + lookup)
```

## Quick Start (Production)

See [DEPLOYMENT.md](DEPLOYMENT.md) for full step-by-step instructions.

```bash
git clone https://github.com/goyibnazarovasliddin/acknowledgement.git
cd acknowledgement
cp .env.example .env
# edit .env with real values
mkdir -p certs && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout certs/privkey.pem -out certs/fullchain.pem \
  -subj "/CN=ack.corp.agrobank.uz/O=Agrobank/C=UZ"
docker compose up -d --build
```

## Local Development (without Docker)

```bash
cd backend
cp .env.example .env
# in .env: DEV_MODE=true, keep SQLite DATABASE_URL

pip install -r requirements.txt

# Windows:
.\run_dev.ps1
# Linux/Mac:
bash run_dev.sh
```

With `DEV_MODE=true` (no real AD), log in on any share link with **any username** and the password **`dev`** to simulate an AD user. Admin panel: `/admin/` (defaults `admin` / `admin123` — change via `.env`).

> **Production:** set `DEV_MODE=false`. The dev login bypass is then disabled and all logins go through real LDAP bind.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy |
| Database | PostgreSQL 15 (SQLite for dev) |
| Auth | Active Directory LDAP bind (`ldap3`) |
| Session | Signed cookies (`itsdangerous`) |
| Frontend | Jinja2 templates + vanilla JS, Chart.js |
| Proxy | Nginx (SSL termination) |
| Runtime | Docker + Docker Compose |
