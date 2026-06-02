$env:DATABASE_URL   = "sqlite:///./acknowledgement.db"
$env:DEV_MODE       = "true"
$env:UPLOAD_DIR     = "./uploads"
$env:SECRET_KEY     = "dev-secret-do-not-use-in-production"
$env:LDAP_SERVER    = if ($env:LDAP_SERVER)    { $env:LDAP_SERVER }    else { "192.168.1.10" }
$env:LDAP_BIND_DN   = if ($env:LDAP_BIND_DN)   { $env:LDAP_BIND_DN }   else { "CN=training,OU=Services Users,OU=Priveleged Accounts,DC=corp,DC=agrobank,DC=uz" }
$env:LDAP_PASSWORD  = if ($env:LDAP_PASSWORD)  { $env:LDAP_PASSWORD }  else { "changeme" }
$env:LDAP_BASE_DN   = if ($env:LDAP_BASE_DN)   { $env:LDAP_BASE_DN }   else { "DC=corp,DC=agrobank,DC=uz" }
$env:PYTHONPATH     = (Resolve-Path ".").Path

New-Item -ItemType Directory -Force -Path "uploads" | Out-Null

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
