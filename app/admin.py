import asyncio
from datetime import UTC, datetime, timedelta
import secrets
from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import func, select, or_, text
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Report, User, VideoVerification
from app.services.users import referral_count
from app.services.badges import badge_status
from app.bot import router as bot_router
from app.miniapp import router as mini_router

app = FastAPI(title="PVP Chat Admin", docs_url=None); security = HTTPBasic(); cfg = settings()
app.include_router(mini_router)
_bot = None
_dispatcher = None
_polling_task = None

def admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(credentials.username, cfg.admin_username) and secrets.compare_digest(credentials.password, cfg.admin_password)
    if not ok: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})

from app.verification import router as verification_router, admin_router as verification_admin_router
app.include_router(verification_router)
app.include_router(verification_admin_router, dependencies=[Depends(admin)])

class Grant(BaseModel): days: int = Field(ge=1, le=365); kind: str = Field(pattern="^(gold)$")
class Moderation(BaseModel): banned: bool
class Verification(BaseModel): verified: bool = True

@app.on_event("startup")
async def startup():
    """Start the HTTP dashboard and Telegram polling in the same Railway service."""
    global _bot, _dispatcher, _polling_task

    await init_db()
    from aiogram import Bot, Dispatcher

    _bot = Bot(cfg.bot_token)
    app.state.bot = _bot
    if cfg.webapp_url:
        from aiogram.types import MenuButtonWebApp, WebAppInfo
        try:
            await _bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="PVP Chat", web_app=WebAppInfo(url=cfg.webapp_url)))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Could not configure Mini App menu button")
    _dispatcher = Dispatcher()
    _dispatcher.include_router(bot_router)
    _polling_task = asyncio.create_task(
        _dispatcher.start_polling(_bot, handle_signals=False),
        name="telegram-polling",
    )


@app.on_event("shutdown")
async def shutdown():
    global _polling_task

    if _dispatcher is not None:
        await _dispatcher.stop_polling()
    if _polling_task is not None:
        _polling_task.cancel()
        await asyncio.gather(_polling_task, return_exceptions=True)
    if _bot is not None:
        await _bot.session.close()

@app.get("/bot", response_class=HTMLResponse)
async def home():
    """Public page for the Railway domain; the chat itself lives in Telegram."""
    bot_username = cfg.public_bot_username.lstrip("@")
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PVP Chat</title><style>body{{font:16px Inter,Arial;background:#09111f;color:#eef2ff;margin:0;min-height:100vh;display:grid;place-items:center}}main{{max-width:520px;text-align:center;padding:36px}}h1{{font-size:42px;margin:0 0 14px}}p{{color:#cbd5e1;line-height:1.6}}a{{display:inline-block;margin-top:18px;padding:14px 22px;border-radius:12px;background:#7c3aed;color:white;text-decoration:none;font-weight:700}}</style></head><body><main><h1>⚔️ PVP Chat</h1><p>Random chat bot Telegram ichida ishlaydi. Suhbatni boshlash uchun botni oching.</p><a href="https://t.me/{bot_username}">Telegram botni ochish</a></main></body></html>'''


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(admin)])
async def dashboard():
    return FileResponse(Path(__file__).parent / "web" / "admin.html")

@app.get("/admin/stats", dependencies=[Depends(admin)])
async def admin_stats():
    async with SessionLocal() as s:
        return {
            "users": await s.scalar(select(func.count(User.telegram_id))) or 0,
            "registered": await s.scalar(select(func.count(User.telegram_id)).where(User.is_registered.is_(True))) or 0,
            "reports": await s.scalar(select(func.count(Report.id))) or 0,
        }

@app.get("/admin/users", dependencies=[Depends(admin)])
async def admin_users(q: str = Query(default="", max_length=128), offset: int = Query(default=0, ge=0)):
    async with SessionLocal() as s:
        query = select(User)
        if q.strip():
            term = q.strip().lstrip("@")
            filters = [User.display_name.icontains(term, autoescape=True), User.username.icontains(term, autoescape=True)]
            if term.isdecimal() and len(term) <= 16:
                filters.append(User.telegram_id == int(term))
            query = query.where(or_(*filters))
        rows = (await s.scalars(query.order_by(User.created_at.desc(), User.telegram_id).offset(offset).limit(26))).all()
        return {"more":len(rows)>25, "users":[{"id":u.telegram_id,"name":u.display_name,"username":u.username,"city":u.city,**badge_status(u),"banned":u.is_banned} for u in rows[:25]]}

@app.get("/users/{user_id}", dependencies=[Depends(admin)])
async def user_detail(user_id: int):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        return {"id":u.telegram_id,"name":u.display_name,"city":u.city,"registered":u.is_registered,"banned":u.is_banned,**badge_status(u),"premium_until":u.premium_until,"gold_until":u.gold_until,"referrals":await referral_count(s, user_id)}

@app.post("/users/{user_id}/verify", dependencies=[Depends(admin)])
async def verify(user_id: int, body: Verification):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        u.is_verified = body.verified; await s.commit()
    return {"ok": True, "verified": body.verified}

@app.post("/users/{user_id}/grant", dependencies=[Depends(admin)])
async def grant(user_id: int, body: Grant):
    async with SessionLocal() as s:
        u = await s.get(User, user_id, with_for_update=True)
        if not u: raise HTTPException(404, "User not found")
        now = datetime.now(UTC); field = "gold_until"
        setattr(u, field, max(getattr(u, field) or now, now) + timedelta(days=body.days)); await s.commit()
    return {"ok": True, "kind": body.kind, "days": body.days}

@app.post("/users/{user_id}/gold/revoke", dependencies=[Depends(admin)])
async def revoke_gold(user_id: int):
    async with SessionLocal() as s:
        u = await s.get(User, user_id, with_for_update=True)
        if not u:
            raise HTTPException(404, "User not found")
        u.gold_until = None
        await s.commit()
    return {"ok": True, "gold": 0}

@app.post("/users/{user_id}/silver/revoke", dependencies=[Depends(admin)])
async def revoke_silver(user_id: int):
    async with SessionLocal() as s:
        u = await s.get(User, user_id, with_for_update=True)
        if not u:
            raise HTTPException(404, "User not found")
        u.silver_verified = False
        verification = await s.get(VideoVerification, user_id, with_for_update=True)
        if verification and verification.status == "approved":
            verification.status = "rejected"
            verification.reason = "Admin verifikatsiyani olib tashladi."
        await s.commit()
    return {"ok": True, "silver": False}

@app.post("/users/{user_id}/moderate", dependencies=[Depends(admin)])
async def moderate(user_id: int, body: Moderation):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        u.is_banned = body.banned
        if body.banned:
            from app.services.matching import leave_queue, active_match, end_match
            await s.execute(text("SELECT pg_advisory_xact_lock(730020)"))
            await leave_queue(s, user_id)
            match = await active_match(s, user_id)
            if match:
                await end_match(s, match)
        await s.commit()
    return {"ok": True, "banned": body.banned}

@app.get("/reports", dependencies=[Depends(admin)])
async def reports():
    async with SessionLocal() as s:
        rows = (await s.scalars(select(Report).order_by(Report.created_at.desc()).limit(100))).all()
    return [{"id":r.id,"reporter":r.reporter_id,"reported":r.reported_id,"match":r.match_id,"reason":r.reason,"at":r.created_at} for r in rows]

@app.post("/leaderboard/reward", dependencies=[Depends(admin)])
async def reward_leaders():
    """Run once at the end of a referral campaign/month; each current top-10 gets 30 Gold days."""
    async with SessionLocal() as s:
        referred, referrer = User.__table__.alias("referred"), User.__table__.alias("referrer")
        ids = (await s.execute(select(referrer.c.telegram_id).join(referred, referred.c.referred_by_id == referrer.c.telegram_id).where(referred.c.referral_rewarded.is_(True)).group_by(referrer.c.telegram_id).order_by(func.count(referred.c.telegram_id).desc()).limit(10))).scalars().all()
        now = datetime.now(UTC)
        for user_id in ids:
            u = await s.get(User, user_id); u.gold_until = max(u.gold_until or now, now) + timedelta(days=cfg.reward_days)
        await s.commit()
    return {"ok": True, "awarded_user_ids": ids, "days": cfg.reward_days}
