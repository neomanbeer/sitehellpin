# Loader Site (Python / Flask)

Web app with API and admin panel for the DLL loader. **All UI and strings are in English** (no encoding issues). Ready for local run and deploy on [Render.com](https://render.com) free tier.

## Requirements

- Python 3.10+
- For **local**: nothing else (uses SQLite).
- For **Render**: PostgreSQL (provided by Render).

## Run locally

No database setup needed (SQLite file is created automatically):

```bash
cd site
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python run_local.py
```

Open **http://127.0.0.1:5000** → redirects to admin login.

- **Admin login**: `admin` / `password`
- **API auth**: POST to `http://127.0.0.1:5000/api/api.php` with `login`, `password`, `data=uncracked`
- **DLL download**: use the `download_url` from the API response (contains a short-lived token)

## Deploy on Render.com (free tier)

1. Push this repo to GitHub/GitLab.
2. On [Render Dashboard](https://dashboard.render.com):
   - **New** → **Blueprint** → connect the repo.
   - Render will read `render.yaml` and create:
     - A **PostgreSQL** database (free 90 days).
     - A **Web Service** (Python) that runs `gunicorn app:app`.
3. After first deploy:
   - Open your app URL (e.g. `https://loader-site-xxx.onrender.com`).
   - Admin is auto-seeded: login **admin** / **password** (change in Settings).
4. **Loader base URL**: set in your C++ loader to  
   `https://YOUR-SERVICE.onrender.com/api/api.php` for auth.  
   Use the `download_url` from the JSON response for the DLL request.

### Render free tier notes

- **Spin-down**: service sleeps after ~15 min inactivity; first request may be slow.
- **Ephemeral disk**: uploaded DLLs in `dll_storage` are lost on redeploy/restart. Re-upload DLL in Admin → DLL after each deploy, or use a paid disk.
- **PostgreSQL**: free DB is limited (90 days on free plan); then upgrade or export your data.

## Project layout

```
site/
  app.py              # Flask app
  config.py           # Config (env vars for Render)
  models.py           # SQLAlchemy models (SQLite + PostgreSQL)
  api_routes.py       # POST /api/api.php (auth), GET /api/download (DLL)
  admin_routes.py     # Admin panel routes
  helpers.py          # Shared helpers
  run_local.py        # Local run with SQLite
  seed_db.py          # Optional: seed admin/settings (app auto-seeds if empty)
  requirements.txt
  render.yaml         # Render Blueprint (DB + Web Service)
  templates/          # Jinja2 (admin, all English)
  dll_storage/        # Uploaded DLLs (create if missing)
```

## API (for C++ loader)

- **POST** `/api/api.php`  
  Body: `application/x-www-form-urlencoded`  
  Fields: `login`, `password`, `data=uncracked`  
  Response JSON: `success`, `message`, `user` (with `download_url` for DLL).

- **GET** `/api/download?token=...`  
  Use the `download_url` from auth response (token inside).  
  Returns DLL binary or 403.

All responses are in English.

## Environment variables (Render / production)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Set by Render when you attach Postgres. Leave unset for local (SQLite). |
| `SECRET_KEY` | Flask secret (Render can generate). |
| `FLASK_DEBUG` | Set to `1` for local debug only. |

## Changing admin password

- **Local**: Admin → Settings → Change password.
- Or run once: `python seed_db.py` (then change in UI).
