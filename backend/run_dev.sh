#!/usr/bin/env bash
# Dev server startup — SQLite, DEV_MODE=true, hot-reload
set -e

export DATABASE_URL="sqlite:///./acknowledgement.db"
export DEV_MODE="true"
export UPLOAD_DIR="./uploads"
export SECRET_KEY="dev-secret-do-not-use-in-production"

# LDAP — point to real server or stub
export LDAP_SERVER="${LDAP_SERVER:-192.168.1.10}"
export LDAP_BIND_DN="${LDAP_BIND_DN:-CN=training,OU=Services Users,OU=Priveleged Accounts,DC=corp,DC=agrobank,DC=uz}"
export LDAP_PASSWORD="${LDAP_PASSWORD:-changeme}"
export LDAP_BASE_DN="${LDAP_BASE_DN:-DC=corp,DC=agrobank,DC=uz}"

mkdir -p uploads

cd "$(dirname "$0")"
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
