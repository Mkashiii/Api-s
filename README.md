# RapidAPI Platform — 48 APIs to Build & Sell (2026)

A complete Python FastAPI platform with **48 production-ready APIs** across 9 categories, featuring authentication, a beautiful white Tailwind CSS UI, and interactive API docs.

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
python run.py
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open in browser

| URL | Description |
|-----|-------------|
| `http://localhost:8000/listing` | Public API catalogue (all 48 APIs) |
| `http://localhost:8000/login` | Login page |
| `http://localhost:8000/dashboard` | User dashboard |
| `http://localhost:8000/admin/dashboard` | Admin dashboard |
| `http://localhost:8000/docs` | Swagger interactive API docs |
| `http://localhost:8000/redoc` | ReDoc API reference |

---

## 🔑 Default Credentials

| Role | Username | Password |
|------|----------|----------|
| 👑 Admin | `admin` | `admin123` |
| 👤 User | `user` | `user123` |

---

## 📦 48 API Categories

| # | Category | Count | Endpoint Prefix |
|---|----------|-------|----------------|
| 1 | 🤖 AI & Natural Language Processing | 8 | `/api/ai/` |
| 2 | 🕷 Data Scraping & Extraction | 6 | `/api/scraping/` |
| 3 | 💰 Finance, Stocks & Crypto | 4 | `/api/finance/` |
| 4 | ✅ Verification, Identity & Communication | 5 | `/api/verify/` |
| 5 | 📰 News, Media & Social Data | 4 | `/api/media/` |
| 6 | 🛠 Developer Utilities & Document Tools | 6 | `/api/tools/` |
| 7 | 🏥 Health, Food, Travel & Lifestyle | 5 | `/api/lifestyle/` |
| 8 | 🗺 Location, Maps & Weather | 4 | `/api/location/` |
| 9 | 🎭 Entertainment, Sports & Miscellaneous | 6 | `/api/entertainment/` |

---

## 📁 Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI app + auth routes
│   ├── auth.py              # JWT + password utilities
│   ├── database.py          # SQLAlchemy + SQLite models
│   └── routers/
│       ├── ai_nlp.py        # APIs 01–08
│       ├── scraping.py      # APIs 09–14
│       ├── finance.py       # APIs 15–18
│       ├── verification.py  # APIs 19–23
│       ├── news_social.py   # APIs 24–27
│       ├── developer_tools.py # APIs 28–33
│       ├── health_lifestyle.py # APIs 34–38
│       ├── location_maps.py # APIs 39–42
│       └── entertainment.py # APIs 43–48
├── templates/
│   ├── base.html            # Base template (Tailwind CSS)
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   ├── listing.html         # Public API catalogue
│   ├── user_dashboard.html  # User dashboard
│   └── admin_dashboard.html # Admin dashboard
├── static/js/main.js
├── run.py                   # Uvicorn entrypoint
├── requirements.txt
└── README.md
```

Built with Python · FastAPI · SQLAlchemy · Tailwind CSS