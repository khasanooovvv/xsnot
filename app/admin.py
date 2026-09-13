from datetime import UTC, datetime, timedelta
import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Report, User
from app.services.users import referral_count

app = FastAPI(title="PVP Chat Admin", docs_url=None); security = HTTPBasic(); cfg = settings()

def admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(credentials.username, cfg.admin_username) and secrets.compare_digest(credentials.password, cfg.admin_password)
    if not ok: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})

class Grant(BaseModel): days: int = Field(ge=1, le=365); kind: str = Field(pattern="^(premium|gold)$")
class Moderation(BaseModel): banned: bool

@app.on_event("startup")
async def startup(): await init_db()

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(admin)])
async def dashboard():
    async with SessionLocal() as s:
        users = await s.scalar(select(func.count(User.telegram_id))) or 0
        registered = await s.scalar(select(func.count(User.telegram_id)).where(User.is_registered.is_(True))) or 0
        reports = await s.scalar(select(func.count(Report.id))) or 0
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>PVP Chat Admin</title><style>body{{font:16px Inter,Arial;background:#09111f;color:#eef2ff;margin:0;padding:48px}}.card{{display:inline-block;background:#111d35;border:1px solid #26385d;border-radius:18px;padding:24px;margin:8px;min-width:180px}}b{{font-size:32px;color:#a78bfa}}code{{color:#7dd3fc}}</style></head><body><h1>⚔️ PVP Chat <span style="color:#a78bfa">Admin</span></h1><div class="card">Jami foydalanuvchi<br><b>{users}</b></div><div class="card">Ro‘yxatdan o‘tgan<br><b>{registered}</b></div><div class="card">Shikoyatlar<br><b>{reports}</b></div><p>API: <code>/users/{{telegram_id}}</code>, <code>/users/{{telegram_id}}/grant</code>, <code>/users/{{telegram_id}}/moderate</code>, <code>/reports</code>, <code>/leaderboard/reward</code></p></body></html>'''

@app.get("/users/{user_id}", dependencies=[Depends(admin)])
async def user_detail(user_id: int):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        return {"id":u.telegram_id,"name":u.display_name,"city":u.city,"registered":u.is_registered,"banned":u.is_banned,"verified":u.is_verified,"premium_until":u.premium_until,"gold_until":u.gold_until,"referrals":await referral_count(s, user_id)}

@app.post("/users/{user_id}/verify", dependencies=[Depends(admin)])
async def verify(user_id: int):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        u.is_verified = True; await s.commit()
    return {"ok": True, "verified": True}

@app.post("/users/{user_id}/grant", dependencies=[Depends(admin)])
async def grant(user_id: int, body: Grant):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        now = datetime.now(UTC); field = "premium_until" if body.kind == "premium" else "gold_until"
        setattr(u, field, max(getattr(u, field) or now, now) + timedelta(days=body.days)); await s.commit()
    return {"ok": True, "kind": body.kind, "days": body.days}

@app.post("/users/{user_id}/moderate", dependencies=[Depends(admin)])
async def moderate(user_id: int, body: Moderation):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u: raise HTTPException(404, "User not found")
        u.is_banned = body.banned; await s.commit()
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
