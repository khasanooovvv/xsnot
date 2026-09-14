import base64
import hashlib
import hmac
import io
import json
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from fastapi import UploadFile, File
from starlette.concurrency import run_in_threadpool
register_heif_opener()
from sqlalchemy import select, func, delete, update, text as sql, or_
from app.config import settings
from app.services.badges import badge_status
from app.services.referral_notifications import send_invite_link
from app.database import SessionLocal
from app.models import User, Match, MatchQueue, MiniAvatar, MiniMessage, Report, ReferralShare, ReferralHistory, VideoVerification
from app.services.users import get_or_create, age_on, days_left, apply_referral_reward, referral_count, consume_share
from app.services.matching import active_match, find_or_queue, end_match, leave_queue

router = APIRouter()

@router.get('/assets/photo-picker.js')
async def photo_picker_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'photo-picker.js', media_type='application/javascript')

@router.get('/assets/verification-camera.js')
async def camera_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'verification-camera.js', media_type='application/javascript')

@router.get('/assets/badges.js')
async def badge_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'badges.js', media_type='application/javascript')

@router.get('/assets/badges.css')
async def badge_styles():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'badges.css', media_type='text/css')

@router.get('/')
async def index():
    return FileResponse(Path(__file__).parent / 'web' / 'index.html')

async def identity(x_telegram_init_data: str = Header(default='')):
    try:
        pairs = parse_qsl(x_telegram_init_data, strict_parsing=True)
        data = dict(pairs)
        if len(pairs) != len(data): raise ValueError()
        signature = data.pop('hash')
        check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', settings().bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected): raise ValueError()
        if not -30 <= time.time() - int(data['auth_date']) <= 86400: raise ValueError()
        account = json.loads(data['user'])
        uid = int(account['id'])
        ref = data.get('start_param', '')
        ref = int(ref[4:]) if ref.startswith('ref_') else None
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Mini App’ni Telegram bot ichidan qayta oching.')
    async with SessionLocal() as s:
        u = await get_or_create(s, uid, account.get('username'), account.get('first_name', 'Player')[:128], ref)
        if u.is_banned: raise HTTPException(403, 'Profil bloklangan.')
        await s.commit()
    return uid

async def registered(uid=Depends(identity)):
    async with SessionLocal() as s:
        u = await s.get(User, uid)
        if not u.is_registered: raise HTTPException(403, 'Avval profilni to‘ldiring.')
    return uid

def normalize_photo(content):
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > 40000000:
                raise ValueError()
            image = ImageOps.exif_transpose(source).convert('RGB')
            output = io.BytesIO()
            image.save(output, format='PNG', compress_level=1)
            return {'image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}
    except Exception:
        raise HTTPException(422, 'Rasm ochilmadi. JPEG, PNG, WebP yoki HEIC rasm tanlang.')

@router.post('/api/photo/prepare')
async def prepare_photo(image: UploadFile = File(...), uid=Depends(identity)):
    try:
        content = await image.read(20 * 1024 * 1024 + 1)
    finally:
        await image.close()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(422, '20 MB dan kichik rasm tanlang.')
    return await run_in_threadpool(normalize_photo, content)

async def profile(s, u, include_avatar=True):
    avatar = await s.get(MiniAvatar, u.telegram_id) if include_avatar else None
    return dict(name=u.display_name, language=u.language, city=u.city, age=age_on(u.birth_date) if u.birth_date else None,
        registered=u.is_registered, **badge_status(u),
        invite_limit=settings().silver_referral_daily_share_limit if u.silver_verified else settings().referral_daily_share_limit,
        referrals=await referral_count(s, u.telegram_id), avatar=avatar.data if avatar else None)

@router.get('/api/me')
async def me(include_avatar: bool = True, uid=Depends(identity)):
    async with SessionLocal() as s: return await profile(s, await s.get(User, uid), include_avatar)

@router.post('/api/delete-account')
async def delete_account(uid=Depends(identity)):
    """Permanently erase every record owned by the authenticated account."""
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730022)'))
        user = await s.get(User, uid, with_for_update=True)
        if not user:
            return {'ok': True, 'deleted': False}
        match_ids = list((await s.scalars(select(Match.id).where(or_(Match.user_one_id == uid, Match.user_two_id == uid)))).all())
        if match_ids:
            await s.execute(delete(MiniMessage).where(MiniMessage.match_id.in_(match_ids)))
            await s.execute(delete(Report).where(Report.match_id.in_(match_ids)))
            await s.execute(delete(Match).where(Match.id.in_(match_ids)))
        await s.execute(delete(Report).where(or_(Report.reporter_id == uid, Report.reported_id == uid)))
        await s.execute(delete(MatchQueue).where(MatchQueue.user_id == uid))
        await s.execute(delete(MiniAvatar).where(MiniAvatar.user_id == uid))
        await s.execute(delete(MiniMessage).where(MiniMessage.sender_id == uid))
        await s.execute(delete(ReferralShare).where(ReferralShare.user_id == uid))
        await s.execute(delete(VideoVerification).where(VideoVerification.user_id == uid))
        if user.referral_rewarded and user.referred_by_id:
            history = await s.scalar(select(ReferralHistory).where(ReferralHistory.referrer_id == user.referred_by_id, ReferralHistory.referred_id == uid))
            if not history:
                s.add(ReferralHistory(referrer_id=user.referred_by_id, referred_id=uid, referred_name=user.display_name))
        # Other accounts may have used this account as their referrer.
        # Break that self-reference before deleting the parent row.
        await s.execute(update(User).where(User.referred_by_id == uid).values(referred_by_id=None))
        await s.delete(user)
        await s.commit()
    return {'ok': True, 'deleted': True}

class ProfileName(BaseModel):
    name: str = Field(min_length=2, max_length=64)

@router.post('/api/profile/name')
async def update_profile_name(body: ProfileName, uid=Depends(registered)):
    name = body.name.strip()
    if len(name) < 2:
        raise HTTPException(422, 'Ism kamida 2 ta belgidan iborat bo‘lsin.')
    async with SessionLocal() as s:
        user = await s.get(User, uid, with_for_update=True)
        user.display_name = name
        await s.commit()
    return {'name': name}

class Registration(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    birthday: date
    city: str = Field(min_length=2, max_length=100)
    accepted: Literal[True]
    avatar: str | None = Field(default=None, max_length=160000000)

@router.post('/api/register')
async def register(body: Registration, uid=Depends(identity)):
    if not 18 <= age_on(body.birthday) <= 120 or not body.city.strip():
        raise HTTPException(422, 'Tug‘ilgan sana yoki shahar noto‘g‘ri. Chat 18+ uchun.')
    avatar = None
    if body.avatar:
        try:
            raw = base64.b64decode(body.avatar.split(',', 1)[1], validate=True)
            with Image.open(io.BytesIO(raw)) as im:
                if im.width * im.height > 40000000: raise ValueError()
                im = im.convert('RGB')
                out = io.BytesIO(); im.save(out, format='PNG', compress_level=1)
                avatar = 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
        except Exception: raise HTTPException(422, 'Rasmni qayta tanlang.')
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730019)'))
        u = await s.get(User, uid)
        u.display_name, u.birth_date, u.city = body.name.strip(), body.birthday, body.city.strip()
        u.is_registered = True
        u.terms_accepted_at, u.terms_version = datetime.now(UTC), settings().terms_version
        if avatar:
            a = await s.get(MiniAvatar, uid)
            if a: a.data = avatar
            else: s.add(MiniAvatar(user_id=uid, data=avatar))
        await apply_referral_reward(s, u)
        await s.commit()
        return await profile(s, u)

class Search(BaseModel):
    mode: Literal['anonymous', 'open'] = 'anonymous'
    city: str = Field(default='', max_length=100)
    min_age: int = Field(default=18, ge=18, le=120)
    max_age: int = Field(default=99, ge=18, le=120)
    accepted: Literal[True]

@router.post('/api/search')
async def search(body: Search, uid=Depends(registered)):
    if body.min_age > body.max_age: raise HTTPException(422, 'Yosh oralig‘i noto‘g‘ri.')
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        await s.execute(delete(MatchQueue).where(MatchQueue.mode.in_(['mini_anonymous', 'mini_open']), MatchQueue.queued_at < datetime.now(UTC) - timedelta(seconds=30)))
        if not await active_match(s, uid):
            await find_or_queue(s, await s.get(User, uid), 'mini_' + body.mode, body.city.strip() or None, body.min_age, body.max_age)
        await s.commit()
    return {'ok': True}

@router.get('/api/chat')
async def chat(after: int = 0, uid=Depends(registered)):
    async with SessionLocal() as s:
        m = await active_match(s, uid)
        if not m or not m.mode.startswith('mini_'):
            queued = await s.get(MatchQueue, uid)
            if queued and queued.mode.startswith('mini_'):
                queued.queued_at = datetime.now(UTC)
                await s.commit()
                return {'status': 'searching'}
            return {'status': 'idle'}
        partner_id = m.user_two_id if m.user_one_id == uid else m.user_one_id
        partner = {'name': 'Anonim', 'avatar': None, 'anonymous': True}
        if m.mode == 'mini_open':
            p = await profile(s, await s.get(User, partner_id))
            partner = {k:p[k] for k in ('name', 'avatar', 'age', 'city', 'verified', 'silver', 'gold')}
        rows = (await s.scalars(select(MiniMessage).where(MiniMessage.match_id == m.id, MiniMessage.id > after).order_by(MiniMessage.id).limit(100))).all()
        return {'status': 'active', 'match': m.id, 'partner': partner, 'messages': [{'id':r.id, 'mine':r.sender_id == uid, 'text':r.text} for r in rows]}

class MessageBody(BaseModel):
    match: int
    text: str = Field(min_length=1, max_length=2000)

@router.post('/api/message')
async def message(body: MessageBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        m = await active_match(s, uid)
        if not m or m.id != body.match or not m.mode.startswith('mini_'): raise HTTPException(409, 'Suhbat tugagan.')
        if not body.text.strip(): raise HTTPException(422, 'Xabar bo‘sh.')
        s.add(MiniMessage(match_id=m.id, sender_id=uid, text=body.text.strip()))
        await s.commit()
    return {'ok': True}

class StopBody(BaseModel):
    reason: str = Field(default='', max_length=1000)

@router.post('/api/stop')
async def stop(body: StopBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        await leave_queue(s, uid)
        m = await active_match(s, uid)
        if m:
            if body.reason.strip():
                s.add(Report(reporter_id=uid, reported_id=m.user_two_id if m.user_one_id == uid else m.user_one_id, match_id=m.id, reason=body.reason.strip()))
            await end_match(s, m)
        await s.commit()
    return {'ok': True}

@router.get('/api/leaders')
async def leaders(uid=Depends(registered)):
    async with SessionLocal() as s:
        refs = User.__table__.alias('refs')
        rows = (await s.execute(select(User, func.count(refs.c.telegram_id)).join(refs, refs.c.referred_by_id == User.telegram_id).where(refs.c.referral_rewarded.is_(True)).group_by(User.telegram_id, User.display_name).order_by(func.count(refs.c.telegram_id).desc(), User.telegram_id).limit(10))).all()
        return [{'name':u.display_name, 'count':count, **badge_status(u)} for u, count in rows]

@router.post('/api/invite')
async def invite(request: Request, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730019)'))
        if not await consume_share(s, uid): raise HTTPException(429, 'Bugungi havola olish limiti tugadi.')
        language = (await s.get(User, uid)).language
        await s.commit()
    link = f'https://t.me/{settings().public_bot_username.lstrip("@")}?start=ref_{uid}'
    sent = await send_invite_link(getattr(request.app.state, 'bot', None), uid, link, language)
    return {'url': link, 'bot_sent': sent}
