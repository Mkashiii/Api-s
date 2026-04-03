"""
RapidAPI Platform — Main FastAPI Application
48 Production-Ready APIs with Admin + User Authentication
"""
import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.database import init_db, get_db, User, APICall, SessionLocal
from app.auth import hash_password, verify_password, generate_api_key, create_access_token

# ── Import all API routers ────────────────────────────────────────────────────
from app.routers.ai_nlp import router as ai_router
from app.routers.scraping import router as scraping_router
from app.routers.finance import router as finance_router
from app.routers.verification import router as verify_router
from app.routers.news_social import router as media_router
from app.routers.developer_tools import router as tools_router
from app.routers.health_lifestyle import router as health_router
from app.routers.location_maps import router as location_router
from app.routers.entertainment import router as entertainment_router


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RapidAPI Platform — 48 APIs",
    description="Build & Sell 48 Production-Ready APIs on RapidAPI",
    version="2026.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    SessionMiddleware,
    secret_key="rapidapi-session-secret-2026",
    session_cookie="rapidapi_session",
    max_age=86400,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Include all API routers ───────────────────────────────────────────────────
app.include_router(ai_router)
app.include_router(scraping_router)
app.include_router(finance_router)
app.include_router(verify_router)
app.include_router(media_router)
app.include_router(tools_router)
app.include_router(health_router)
app.include_router(location_router)
app.include_router(entertainment_router)


# ── Auth helpers ─────────────────────────────────────────────────────────────

def get_current_user(request: Request, db: Session = None):
    username = request.session.get("username")
    role = request.session.get("role")
    if not username:
        return None
    return {"username": username, "role": role}


def require_login(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


# ── Startup — seed default users ─────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        # Create admin user
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@rapidapi.local",
                hashed_password=hash_password("admin123"),
                role="admin",
                api_key=generate_api_key(),
            )
            db.add(admin)

        # Create demo user
        if not db.query(User).filter(User.username == "user").first():
            demo = User(
                username="user",
                email="user@rapidapi.local",
                hashed_password=hash_password("user123"),
                role="user",
                api_key=generate_api_key(),
            )
            db.add(demo)

        db.commit()
    finally:
        db.close()


# ── Public pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_current_user(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse("/admin/dashboard", status_code=302)
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/listing", status_code=302)


@app.get("/listing", response_class=HTMLResponse)
def api_listing(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("listing.html", {"request": request, "user": user})


# ── Login / Logout ────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None, next: str = "/"):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "next": next})


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == username).first()
        if not db_user or not verify_password(password, db_user.hashed_password):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password.", "next": next},
                status_code=400,
            )
        request.session["username"] = db_user.username
        request.session["role"] = db_user.role
        request.session["user_id"] = db_user.id
        if db_user.role == "admin":
            return RedirectResponse("/admin/dashboard", status_code=302)
        return RedirectResponse("/dashboard", status_code=302)
    finally:
        db.close()


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/listing", status_code=302)


# ── User Dashboard ────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?next=/dashboard", status_code=302)
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == user["username"]).first()
        recent_calls = (
            db.query(APICall)
            .filter(APICall.user_id == db_user.id)
            .order_by(APICall.called_at.desc())
            .limit(20)
            .all()
        )
        return templates.TemplateResponse(
            "user_dashboard.html",
            {
                "request": request,
                "user": user,
                "db_user": db_user,
                "recent_calls": recent_calls,
            },
        )
    finally:
        db.close()


# ── Admin Dashboard ───────────────────────────────────────────────────────────

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse("/login?next=/admin/dashboard", status_code=302)
    db = SessionLocal()
    try:
        all_users = db.query(User).all()
        all_calls = db.query(APICall).order_by(APICall.called_at.desc()).limit(50).all()
        stats = {
            "total_users": len(all_users),
            "total_calls": db.query(APICall).count(),
            "active_users": sum(1 for u in all_users if u.is_active),
        }
        return templates.TemplateResponse(
            "admin_dashboard.html",
            {
                "request": request,
                "user": user,
                "users": all_users,
                "recent_calls": all_calls,
                "stats": stats,
            },
        )
    finally:
        db.close()


@app.post("/admin/users")
def admin_create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            api_key=generate_api_key(),
        )
        db.add(new_user)
        db.commit()
        return RedirectResponse("/admin/dashboard", status_code=302)
    except Exception:
        db.rollback()
        return RedirectResponse("/admin/dashboard?error=user_exists", status_code=302)
    finally:
        db.close()


@app.post("/admin/users/{user_id}/toggle")
def admin_toggle_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.is_active = not db_user.is_active
            db.commit()
        return RedirectResponse("/admin/dashboard", status_code=302)
    finally:
        db.close()


# ── Register ──────────────────────────────────────────────────────────────────

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = None):
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Username or email already exists."},
                status_code=400,
            )
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role="user",
            api_key=generate_api_key(),
        )
        db.add(new_user)
        db.commit()
        return RedirectResponse("/login?registered=1", status_code=302)
    except Exception:
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Registration failed. Please try again."},
            status_code=500,
        )
    finally:
        db.close()
