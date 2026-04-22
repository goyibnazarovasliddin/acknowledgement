# Ishga Tushirish Yo'riqnomasi

> 🇺🇿 O'zbekcha &nbsp;|&nbsp; 🇬🇧 [English](DEPLOYMENT.md)

Production deploy: Docker + PostgreSQL + Active Directory LDAP.

## Autentifikatsiya qanday ishlaydi

Xodimlar hujjat havolasini ochadi → ilova ularni `REMOTE_USER` HTTP headeri orqali aniqlaydi. **Bu headerni IIS yoki Apache Kerberos/NTLM autentifikatsiyasi orqali o'rnatadi.**

```
Brauzer → IIS yoki Apache (Kerberos/NTLM → REMOTE_USER o'rnatadi) → Nginx → Ilova → AD LDAP
```

Bu proxy bo'lmasa, xodimlar "Kirish cheklangan" sahifasini ko'radi. Admin panel (`/admin`) SSO talab qilmaydi — o'z login/parol tizimi bor.

---

## Talablar

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

## 1-qadam — Repozitoriyani clone qilish

```bash
git clone https://github.com/goyibnazarovasliddin/acknowledgement.git
cd acknowledgement
```

---

## 2-qadam — `.env` fayl yaratish

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

## 3-qadam — SSL sertifikat

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

## 4-qadam — AD ulanishini tekshirish

```bash
nc -zv <LDAP_SERVER IP> 389
# Kutilgan natija: Connection to <IP> 389 port [tcp/ldap] succeeded!
```

Port 389 blok bo'lsa → tarmoq admininizdan ushbu serverdan AD hostiga `TCP/389` ochib berishini so'rang.

---

## 5-qadam — Build va ishga tushirish

```bash
docker compose up -d --build
```

```bash
docker compose ps
# Uchala container ham Up bo'lishi kerak: app, db, nginx
```

---

## 6-qadam — Tekshirish

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

## 7-qadam — SSO proxy sozlash (xodimlar uchun majburiy)

Muhitingizga qarab **bitta variantni** tanlang.

---

### A variant — Windows Server (IIS)

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
ports:
  - "127.0.0.1:8080:80"
```

---

### B variant — Linux Server (Apache + mod_auth_kerb)

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

### C variant — Linux Server (Apache + NTLM)

Kerberos sozlanmagan bo'lsa, NTLM ishlaydi. `libapache2-mod-auth-ntlm-winbind` va domenga qo'shilgan Winbind kerak. AD admininizdan domen qo'shilishi uchun yordam so'rang — Apache konfiguratsiyasi B variant bilan bir xil, faqat `AuthType NTLM`.

---

## SSO sozlangandan keyin arxitektura

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

## Muhit o'zgaruvchilari

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

## Foydali buyruqlar

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

## Muammolarni bartaraf etish

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
