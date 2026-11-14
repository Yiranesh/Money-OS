# Money OS 🇲🇾

> **"The page prints your budget."** — A tactile, thermal-receipt personal budgeting application built for university students and first-time earners in Malaysia.

Money OS is a complete web project featuring a responsive frontend and a robust Python/Flask backend with SQLite persistence, rate limiting, and an admin dashboard.

---

## ⚡ How to Run

### Windows (PowerShell)

```powershell
# 1. Navigate to the project directory
cd money-os

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install required packages
pip install -r requirements.txt

# 4. Copy environment configuration
Copy-Item .env.example .env

# 5. Run the application
python app.py
```

The application will start at **http://localhost:5000** (or the port specified by `$env:PORT`).

---

### Mac / Linux (Bash or Zsh)

```bash
# 1. Navigate to the project directory
cd money-os

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install required packages
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Run the application (development)
python3 app.py

# Or run with production WSGI server (Gunicorn)
gunicorn app:app --bind 0.0.0.0:5000
```

---

## 🚀 Deploy to Render

Money OS is pre-configured for one-click deployment on [Render](https://render.com) using the included `render.yaml` blueprint.

### Step-by-Step Instructions

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: complete Money OS project"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```

2. **Create a Blueprint or Web Service on Render**:
   - Log into your [Render Dashboard](https://dashboard.render.com).
   - Click **New +** > **Blueprint** and select your GitHub repository (Render will automatically detect `render.yaml`).
   - *Alternatively, click **New +** > **Web Service**:*
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`

3. **Set Environment Variables in Render Dashboard**:
   - Under your service's **Environment** tab, set:
     - `ADMIN_PASSWORD`: Your secret admin password (e.g. `MySecureAdminKey2026!`).
     - `DATABASE_PATH`: `money_os.db` (default).
     - `FLASK_ENV`: `production`.

4. **Deploy**:
   - Render will build and deploy your application. Once finished, your site will be live at:
     ```
     https://<your-service-name>.onrender.com
     ```

> ⚠️ **Important Note on Render Free Tier**:  
> Render's free tier uses an ephemeral filesystem. If your web service spins down after inactivity, SQLite database records (`money_os.db`) will reset to empty. For persistent data across restarts, upgrade to a Render disk or connect a managed Postgres database.

---

## 🧪 Running Tests

A complete test suite (`pytest`) is included in `tests/test_api.py`, covering validation, calculations, duplicate handling, admin auth, and rate limits.

```bash
# Run the test suite
pytest tests/test_api.py -v
```

All 26 test cases cover:
- `GET /health` status response
- `GET /` and `404` custom receipt page handling
- `POST /api/budget` calculation and boundary validations
- `POST /api/waitlist` email formatting and 409 duplicate rejection
- `POST /api/questions` length and required field validations
- `GET /api/stats` aggregated metrics
- `GET /admin/waitlist` HTTP Basic authentication & CSV export
- Rate limiting (exceeding 10 requests per minute returns HTTP 429)

---

## 📐 Project Structure

```
money-os/
├── app.py                 # Flask server, API endpoints, SQLite helpers & rate limiting
├── requirements.txt       # Production & test dependencies
├── render.yaml            # Render Blueprint deployment configuration
├── README.md              # Project documentation and run guide
├── .env.example           # Environment template
├── .gitignore             # Excludes .env, money_os.db, __pycache__, .venv, *.zip
├── templates/
│   ├── index.html         # Main welcome page ("The page prints your budget")
│   └── 404.html           # Custom 404 error slip page
├── static/
│   ├── style.css          # Design system, thermal receipt styling & CSS torn edges
│   ├── app.js             # Vanilla JS: debounced budget sync, dialogs & form handling
│   └── favicon.svg        # Crisp vector badge favicon
└── tests/
    └── test_api.py        # 26 comprehensive pytest unit & integration tests
```

---

## 🔌 API Reference

| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/` | Serves the main landing page | Unlimited |
| `GET` | `/health` | Healthcheck returning `{"status":"ok"}` | Unlimited |
| `POST` | `/api/budget` | Calculates & persists 50/30/20 split (`{"income": number}`) | 10 / min |
| `POST` | `/api/waitlist` | Joins the student waitlist (`{"email": string}`) | 10 / min |
| `POST` | `/api/questions` | Submits a question (`{"name", "email", "message"}`) | 10 / min |
| `GET` | `/api/stats` | Returns `{"waitlist_count", "budgets_created"}` | Unlimited |
| `GET` | `/admin/waitlist`| Protected HTML dashboard (HTTP Basic Auth) | Unlimited |
| `GET` | `/admin/export-csv`| Downloads waitlist entries as a `.csv` file | Unlimited |

---

## ⚖️ Legal Disclaimer

Money OS is a budgeting tool for learning and planning. It does not give financial advice.
