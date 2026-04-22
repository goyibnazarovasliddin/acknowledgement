# Ishga Tushirish Yo'riqnomasi / Deployment Guide

---

## 🇺🇿 O'zbekcha

### Autentifikatsiya qanday ishlaydi

Xodimlar hujjat havolasini ochadi → ilova ularni `REMOTE_USER` HTTP headeri orqali aniqlaydi. **Bu headerni IIS yoki Apache Kerberos/NTLM autentifikatsiyasi orqali o'rnatadi.**

```
Brauzer → IIS yoki Apache (Kerberos/NTLM → REMOTE_USER o'rnatadi) → Nginx → Ilova → AD LDAP
```

Bu proxy bo'lmasa, xodimlar "Kirish cheklangan" sahifasini ko'radi. Admin panel (`/admin`) SSO talab qilmaydi — o'z login/parol tizimi bor.

---

### Talablar

| Talab | Versiya |
|-------|---------|
| Docker | 24+ |
| Docker Compose | v2 (`docker compose`) |
| OS | Ubuntu 22.04 / Debian 12 / RHEL 8+ |
| RAM | Kamida 2 GB |
| Disk | Kamida 20 GB |
| Tarmoq | Server AD ga TCP/389 orqali ulanishi kerak |

Docker o'rnatish (agar yo'q bo'lsa):
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

### 1-qadam — Repozitoriyani clone qilish

```bash
git clone https://github.com/YOUR_ORG/acknowledgement.git
cd acknowledgement
```

---

### 2-qadam — `.env` fayl yaratish

```bash
cp .env.example .env
nano .env
```

**Barcha majburiy qiymatlarni to'ldiring:**

```env
# PostgreSQL
POSTGRES_USER=ack_user
POSTGRES_PASSWORD=<kuchli parol>
POSTGRES_DB=acknowledgement

# Active Directory
LDAP_SERVER=<AD server IP>
LDAP_BIND_DN=CN=training,OU=Services Users,OU=Priveleged Accounts,DC=corp,DC=agrobank,DC=uz
LDAP_PASSWORD=<servis akkaunt paroli>
LDAP_BASE_DN=DC=corp,DC=agrobank,DC=uz

# SECRET_KEY generatsiya qilish:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<kamida 32 belgili random string>

# Admin panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<kuchli parol>
ADMIN_EMAIL=<email manzilingiz>
```

> **Diqqat:** `.env` faylini hech qachon gitga commit qilmang. U `.gitignore` da ro'yxatda.

---

### 3-qadam — SSL sertifikat

**A variant — Self-signed** (ichki tarmoq uchun):
```bash
mkdir -p certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -subj "/CN=ack.corp.agrobank.uz/O=Agrobank/C=UZ"
```

**B variant — Mavjud korporativ sertifikat:**
```bash
mkdir -p certs
cp /path/to/your/fullchain.pem certs/fullchain.pem
cp /path/to/your/privkey.pem   certs/privkey.pem
```

---

### 4-qadam — AD ulanishini tekshirish

```bash
nc -zv <LDAP_SERVER IP> 389
# Kutilgan natija: Connection to <IP> 389 port [tcp/ldap] succeeded!
```

Port 389 blok bo'lsa → tarmoq admininizdan ushbu serverdan AD hostiga `TCP/389` ochib berishini so'rang.

---

### 5-qadam — Build va ishga tushirish

```bash
docker compose up -d --build
```

```bash
docker compose ps
# Uchala container ham Up bo'lishi kerak: app, db, nginx
```

---

### 6-qadam — Tekshirish

```bash
# Admin panel ishlayaptimi:
curl -k https://localhost/admin/login

# Container ichidan LDAP testi:
docker compose exec app python3 -c "
from app.auth.ldap_client import ldap_client
print(ldap_client.get_user_info('ism.familiya'))
"
```

---

### 7-qadam — SSO proxy sozlash (xodimlar uchun majburiy)

Muhitingizga qarab **bitta variantni** tanlang.

---

#### A variant — Windows Server (IIS)

Docker ishlaydigan server Windows bo'lsa yoki alohida Windows Server mavjud bo'lsa ishlatiladi.

**Talab:** Windows Server + IIS + `Application Request Routing (ARR)` + `Windows Authentication` modullari.

**1. IIS modullarini o'rnatish:**
- *Server Manager → Add Roles and Features*
- Qo'shing: `Web Server (IIS)` → `Security` → `Windows Authentication`
- [Application Request Routing (ARR)](https://www.iis.net/downloads/microsoft/application-request-routing) yuklab o'rnating

**2. IIS da yangi sayt yarating:**
- HTTPS 443 portida (yoki 80)
- Jismoniy yo'l: istalgan bo'sh papka

**3. Windows Authentication yoqing:**
- Saytni tanlang → *Authentication*
- `Anonymous Authentication` → O'chirish
- `Windows Authentication` → Yoqish

**4. Docker ilovaga reverse proxy sozlang (`web.config`):**
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

> IIS Windows Authentication muvaffaqiyatli bo'lgach `REMOTE_USER` headerni `DOMAIN\username` formatida avtomatik o'rnatadi. Ilova `DOMAIN\` qismini o'zi olib tashlaydi.

**5. `docker-compose.yml` nginx portini yangilang** (IIS endi SSL ni boshqaradi):
```yaml
# docker-compose.yml — nginx ports
ports:
  - "127.0.0.1:8080:80"
```

---

#### B variant — Linux Server (Apache + mod_auth_kerb)

Server Linux bo'lsa va AD da Kerberos sozlangan bo'lsa ishlatiladi.

**1. Apache va Kerberos modulini o'rnatish:**
```bash
apt install apache2 libapache2-mod-auth-kerb krb5-user -y
a2enmod auth_kerb proxy proxy_http headers ssl
```

**2. AD admininizdan keytab oling** (HTTP/hostname@REALM uchun).

**3. Apache virtual host yarating** `/etc/apache2/sites-available/ack.conf`:
```apache
<VirtualHost *:443>
    ServerName ack.corp.agrobank.uz

    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/fullchain.pem
    SSLCertificateKeyFile /etc/ssl/private/privkey.pem

    <Location />
        AuthType Kerberos
        AuthName "Agrobank Korporativ Kirish"
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

**4. Saytni yoqing va qayta ishga tushiring:**
```bash
a2ensite ack
systemctl restart apache2
```

**5. `docker-compose.yml` nginx portini yangilang:**
```yaml
ports:
  - "127.0.0.1:8080:80"
```

---

#### C variant — Linux Server (Apache + NTLM)

Kerberos sozlanmagan bo'lsa, NTLM ishlaydi. `libapache2-mod-auth-ntlm-winbind` va domenga qo'shilgan Winbind kerak. AD admininizdan domen qo'shilishi uchun yordam so'rang — Apache konfiguratsiyasi B variant bilan bir xil, faqat `AuthType NTLM`.

---

### SSO sozlangandan keyin arxitektura

```
Xodim brauzeri
      │
      ▼
IIS (Windows Auth) yoki Apache (mod_auth_kerb)
  → AD da Kerberos/NTLM orqali autentifikatsiya
  → Header o'rnatadi: REMOTE_USER: CORP\ism.familiya
      │
      ▼
Nginx (Docker, 8080 ichki port)
  → REMOTE_USER headerni uzatadi
      │
      ▼
FastAPI ilovasi
  → REMOTE_USER ni o'qiydi
  → LDAP orqali AD dan foydalanuvchi ma'lumotlarini oladi
  → Xodimga hujjatni ko'rsatadi
```

---

### Muhit o'zgaruvchilari

| O'zgaruvchi | Majburiy | Tavsif |
|-------------|----------|--------|
| `POSTGRES_USER` | Ha | PostgreSQL foydalanuvchi nomi |
| `POSTGRES_PASSWORD` | Ha | PostgreSQL paroli |
| `POSTGRES_DB` | Ha | PostgreSQL ma'lumotlar bazasi nomi |
| `LDAP_SERVER` | Ha | Active Directory server IP |
| `LDAP_BIND_DN` | Ha | Servis akkaunt to'liq DN |
| `LDAP_PASSWORD` | Ha | Servis akkaunt paroli |
| `LDAP_BASE_DN` | Ha | AD qidiruv bazasi |
| `SECRET_KEY` | Ha | Cookie imzolash kaliti (kamida 32 belgi) |
| `ADMIN_USERNAME` | Ha | Admin panel foydalanuvchi nomi |
| `ADMIN_PASSWORD` | Ha | Admin panel paroli |
| `ADMIN_EMAIL` | Ha | Bloklangan foydalanuvchilarga ko'rsatiladi |
| `ADMIN_SESSION_HOURS` | Yo'q | Sessiya davomiyligi (standart: 8) |
| `MAX_FILE_SIZE_MB` | Yo'q | Yuklash chegarasi (standart: 100) |
| `MAX_DECLINE_ATTEMPTS` | Yo'q | Rad etish chegarasi (standart: 3) |
| `SCROLL_THRESHOLD` | Yo'q | Talab qilinadigan scroll % (standart: 0.90) |
| `MIN_VIEW_SECONDS` | Yo'q | Minimal o'qish vaqti (standart: 20) |

---

### Foydali buyruqlar

```bash
# To'xtatish
docker compose down

# To'xtatish va barcha ma'lumotlarni o'chirish (DB + uploads)
docker compose down -v

# Loglarni ko'rish
docker compose logs -f app

# Faqat ilovani qayta ishga tushirish
docker compose restart app

# git pull dan keyin yangilash
git pull
docker compose up -d --build
```

---

### Muammolarni bartaraf etish

| Belgi | Sabab | Yechim |
|-------|-------|--------|
| `502 Bad Gateway` | Container hali tayyor emas | 10s kuting, `docker compose logs app` ko'ring |
| `LDAP bind failed` | Noto'g'ri parol yoki DN | `.env` da `LDAP_PASSWORD` va `LDAP_BIND_DN` tekshiring |
| `Connection refused :389` | Firewall LDAP ni bloklaydi | Serverdan AD hostiga TCP/389 ochilsin |
| `SSL handshake error` | Sertifikat fayllari yo'q | 3-qadamni qayta bajaring |
| `db not healthy` | Noto'g'ri `POSTGRES_*` qiymatlar | `.env` tekshiring, `docker compose down -v` bajaring |
| Admin kirish ishlamaydi | Noto'g'ri `ADMIN_PASSWORD` | `.env` tekshiring, `docker compose restart app` |
| Xodimlar "Kirish cheklangan" ko'radi | `REMOTE_USER` header yo'q | 7-qadamda IIS yoki Apache SSO proxy sozlang |
| Kerberos auth ishlamaydi | Keytab muddati tugagan | AD admininizdan yangi keytab oling |

---
---

## 🇬🇧 English

### How authentication works

Employees open a document link → the app reads the `REMOTE_USER` HTTP header to identify them. **This header must be set by an upstream authentication proxy (IIS or Apache) that performs Kerberos/NTLM authentication against Active Directory.**

```
Browser → IIS or Apache (Kerberos/NTLM → sets REMOTE_USER) → Nginx → App → AD LDAP lookup
```

Without this proxy in front, employees will see "Kirish cheklangan" (access restricted). The admin panel (`/admin`) does NOT require SSO — it uses its own username/password login.

---

### Prerequisites

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

### Step 1 — Clone the repository

```bash
git clone https://github.com/YOUR_ORG/acknowledgement.git
cd acknowledgement
```

---

### Step 2 — Create `.env`

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

### Step 3 — SSL Certificate

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

### Step 4 — Verify AD connectivity

```bash
nc -zv <LDAP_SERVER IP> 389
# Expected: Connection to <IP> 389 port [tcp/ldap] succeeded!
```

If port 389 is blocked → ask your network admin to allow `TCP/389` from this server to the AD host.

---

### Step 5 — Build and start

```bash
docker compose up -d --build
```

```bash
docker compose ps
# All three containers must be Up: app, db, nginx
```

---

### Step 6 — Verify

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

### Step 7 — Configure SSO proxy (required for employees)

Choose **one** option based on your environment.

---

#### Option A — Windows Server (IIS)

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

#### Option B — Linux Server (Apache + mod_auth_kerb)

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

#### Option C — Linux Server (Apache + NTLM)

Use this if Kerberos is not configured but NTLM works. Requires `libapache2-mod-auth-ntlm-winbind` and Winbind joined to the domain. Contact your AD admin for domain join procedure — Apache config is identical to Option B but with `AuthType NTLM`.

---

### Architecture after SSO setup

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

### Environment variables reference

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

### Useful commands

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

### Troubleshooting

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
