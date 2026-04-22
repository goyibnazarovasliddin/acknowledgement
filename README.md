# Document Acknowledgement System

> 🇺🇿 [O'zbekcha](README.uz.md) &nbsp;|&nbsp; 🇬🇧 English

Internal document acknowledgement tracking for Agrobank employees.

Employees open a unique link, confirm their AD identity, read the document, and acknowledge it. Admins track who has and hasn't acknowledged.

## Features

- SSO via Active Directory (Kerberos/NTLM — `REMOTE_USER` header from IIS/Apache)
- LDAP user info lookup (name, department, email)
- PDF/document viewer with scroll and time enforcement
- Admin panel: upload documents, track acknowledgements, export CSV/Excel
- Audit log of every open, confirm, and acknowledge event
- PostgreSQL in production, SQLite for local dev

## Architecture

```
Browser → IIS/Apache (Kerberos auth) → Nginx (SSL) → FastAPI → PostgreSQL
                                                          ↓
                                              Active Directory (LDAP)
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

With `DEV_MODE=true`, use `X-Dev-User: DOMAIN\username` header or the dev test page at `/dev/`.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy |
| Database | PostgreSQL 15 (SQLite for dev) |
| Auth | Active Directory LDAP (`ldap3`) |
| Session | Signed cookies (`itsdangerous`) |
| Frontend | Jinja2 templates + vanilla JS |
| Proxy | Nginx (SSL termination) |
| Runtime | Docker + Docker Compose |
