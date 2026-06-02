# Hujjatlarni Tasdiqlash Tizimi

> 🇺🇿 O'zbekcha &nbsp;|&nbsp; 🇬🇧 [English](README.md)

Agrobank xodimlari uchun ichki hujjatlarni tasdiqlash tizimi.

Xodim unikal havola orqali kiradi, o'z AD login-parolini kiritadi, ko'rsatilgan ma'lumotni tasdiqlaydi, hujjatni o'qiydi va tanishib chiqadi. Admin kim tanishganini va kimlar hali tanishmaganini real vaqtda kuzatib boradi.

## Imkoniyatlar

- **AD login** — foydalanuvchi o'z AD login + parolini kiritadi (LDAP bind). SSO/Kerberos shart emas.
- **Shaxsni tasdiqlash** — login'dan keyin FISH, tarkibiy tuzilma va lavozim ko'rsatiladi ("Bu sizmi?"). Rad etilsa qayta login so'raladi; 3 marta xato bo'lsa "admin bilan bog'laning" deyiladi.
- **Hujjat ko'rish** — PDF inline, scroll (≥ chegaradan) va minimal vaqt o'tmaguncha "Tanishib chiqdim" ochilmaydi. Scroll talabi faqat PDF uchun.
- **Urinish-asosli hisobot** — har ochish alohida urinish. Hujjat jadvalida har user uchun bitta qator (eng birinchi urinish); user ustiga bosilsa barcha urinishlari chiqadi. Real vaqtda yangilanadi.
- **Admin analitika** — KPI cardlar (AD jami xodimlar, tarkibiy tuzilmalar, qamrov %) va grafiklar (tanishgan/tanishmagan, bo'limlar bo'yicha, 30 kunlik trend).
- **Arxiv + deep arxiv** — hujjatni arxivlash (yashirin, data saqlanadi) va tiklash. Arxivdan o'chirilsa to'liq snapshot yashirin `deep_archive` jadvalga ko'chadi — DB darajasida hech narsa yo'qolmaydi.
- **Eksport** — CSV / Excel (openpyxl), har hujjat uchun.
- **i18n** — O'zbek / Rus. Barcha vaqtlar qat'iy displey zonasida (Toshkent/Ashxabod, UTC+5).

## Arxitektura

```
Brauzer → Nginx (SSL) → FastAPI → PostgreSQL
                           ↓
               Active Directory (LDAP bind + lookup)
```

## Tezkor ishga tushirish (Production)

To'liq yo'riqnoma uchun [DEPLOYMENT.uz.md](DEPLOYMENT.uz.md) ga qarang.

```bash
git clone https://github.com/goyibnazarovasliddin/acknowledgement.git
cd acknowledgement
cp .env.example .env
# .env faylini haqiqiy qiymatlar bilan to'ldiring
mkdir -p certs && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout certs/privkey.pem -out certs/fullchain.pem \
  -subj "/CN=ack.corp.agrobank.uz/O=Agrobank/C=UZ"
docker compose up -d --build
```

## Local Development (Docker siz)

```bash
cd backend
cp .env.example .env
# .env da: DEV_MODE=true, SQLite DATABASE_URL

pip install -r requirements.txt

# Windows:
.\run_dev.ps1
# Linux/Mac:
bash run_dev.sh
```

`DEV_MODE=true` da (real AD yo'q) istalgan havolada **istalgan username** + parol **`dev`** bilan kirib AD foydalanuvchisini simulyatsiya qilish mumkin. Admin panel: `/admin/` (default `admin` / `admin123` — `.env` orqali o'zgartiring).

> **Production:** `DEV_MODE=false` qiling. Shunda dev login bypass o'chadi va barcha login real LDAP bind orqali o'tadi.

## Texnologiyalar

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | FastAPI + SQLAlchemy |
| Ma'lumotlar bazasi | PostgreSQL 15 (dev uchun SQLite) |
| Autentifikatsiya | Active Directory LDAP bind (`ldap3`) |
| Session | Imzolangan cookie (`itsdangerous`) |
| Frontend | Jinja2 shablonlar + vanilla JS, Chart.js |
| Proxy | Nginx (SSL termination) |
| Runtime | Docker + Docker Compose |
