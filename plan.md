# Feed the City — Sandwich Ingredient Tracker

## Context
~200 volunteers buying sandwich ingredients for ~1500 total sandwiches. Volunteers buy whatever's needed, then log what they actually purchased. App tracks per-ingredient progress.

## Stack
Flask + Turso (libsql) + Tailwind CDN. Deploys to Vercel. Conda env: `feed_the_city` (Python 3.12).

## File Structure
```
feed_the_city/
├── app.py              # Flask app, all routes + API
├── db.py               # DB init, connection helpers, WAL mode
├── schema.sql          # SQLite schema
├── vercel.json         # Vercel deployment config
├── requirements.txt    # flask, libsql-experimental, gunicorn
├── static/
│   └── app.js          # API calls, polling, purchase form
└── templates/
    ├── base.html       # Shared layout + Tailwind CDN
    ├── index.html      # Volunteer page (see needs + log purchases)
    ├── dashboard.html  # Per-ingredient progress bars
    └── admin.html      # Recipe management + target toggle
```

## Database Schema
- **recipe** — `target_sandwiches`, `target_enabled` (toggle)
- **ingredient** — `name`, `qty_per_sandwich`, `unit`, `package_size`, `package_unit`, `display_note`
- **purchase** — `volunteer_name`, `volunteer_phone`, `created_at`
- **purchase_item** — `purchase_id`, `ingredient_id`, `quantity` (what they actually bought)

## Core Flow
1. Admin sets recipe (ingredients per sandwich) + target count (toggleable)
2. Volunteer visits `/` → sees per-ingredient progress ("still need X slices of bread")
3. Volunteer buys whatever's needed at the store
4. Volunteer logs actual quantities purchased per ingredient
5. Dashboard at `/dashboard` shows per-ingredient progress bars + recent purchases

## Status (2026-03-14)
- [x] Conda env created (`feed_the_city`, Python 3.12)
- [x] Database schema + init
- [x] All API endpoints (status, purchase, admin recipe/toggle/reset)
- [x] All templates (volunteer, dashboard, admin)
- [x] Client-side JS (polling, purchase form, admin panel)
- [x] End-to-end API tests pass (libsql)
- [x] Vercel config (`vercel.json`)
- [x] Turso support in db.py (falls back to local SQLite if no env vars)
- [x] Session security hardened (HttpOnly, SameSite=Lax, Secure on Vercel)
- [x] `.gitignore` (*.db, __pycache__, .vercel, .env, *.DS_STORE)
- [ ] Turso DB created + Vercel env vars set
- [ ] Deploy to Vercel
- [ ] Live browser testing

## Dev Commands
```bash
conda activate feed_the_city
python3 app.py  # localhost:5000
```

## Deploy to Vercel
1. Create Turso DB: `turso db create feed-the-city`
2. Get URL: `turso db show feed-the-city --url`
3. Get token: `turso db tokens create feed-the-city`
4. Set Vercel env vars: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `SECRET_KEY`, `ADMIN_PASSWORD`
5. `vercel deploy`

## Admin
- Default password: `feedthecity` (override via `ADMIN_PASSWORD` env var)
- Admin page at `/admin`
