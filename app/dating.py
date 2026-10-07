import base64
import io
import json
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
from sqlalchemy import select, or_
from starlette.concurrency import run_in_threadpool
from app.database import SessionLocal
from app.models import User
from app.dating_models import DatingProfile, DatingVote
from app.direct_models import BlockedUser
from app.miniapp import registered
from app.services.subscriptions import subscription

router = APIRouter()

@router.get('/assets/navigation.js')
async def navigation_script():
    return FileResponse(Path(__file__).parent / 'web/assets/navigation.js', media_type='application/javascript', headers={'Cache-Control': 'no-cache'})

@router.get('/assets/navigation.css')
async def navigation_style():
    return FileResponse(Path(__file__).parent / 'web/assets/navigation.css', media_type='text/css', headers={'Cache-Control': 'no-cache'})

@router.get('/assets/dating.js')
async def script():
    return FileResponse(Path(__file__).parent / 'web/assets/dating.js', media_type='application/javascript', headers={'Cache-Control': 'no-cache'})

@router.get('/assets/dating.css')
async def style():
    return FileResponse(Path(__file__).parent / 'web/assets/dating.css', media_type='text/css', headers={'Cache-Control': 'no-cache'})

class ProfileBody(BaseModel):
    bio: str = Field(default='', max_length=300)
    photos: list[str] = Field(max_length=6)

class VoteBody(BaseModel):
    liked: bool

def normalize_photos(photos):
    result = []
    for value in photos:
        try:
            if len(value) > 14 * 1024 * 1024 or not value.startswith('data:image/'):
                raise ValueError()
            content = base64.b64decode(value.split(',', 1)[1], validate=True)
            if len(content) > 10 * 1024 * 1024:
                raise ValueError()
            with Image.open(io.BytesIO(content)) as source:
                if source.width * source.height > 40_000_000:
                    raise ValueError()
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((1200, 1600))
                output = io.BytesIO()
                image.save(output, 'JPEG', quality=85)
            result.append('data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode())
        except Exception:
            raise HTTPException(422, '10 MB gacha bo‘lgan to‘g‘ri rasm tanlang.')
    return result

def card(user, profile):
    today = date.today()
    age = None if not user.birth_date else today.year-user.birth_date.year-((today.month,today.day)<(user.birth_date.month,user.birth_date.day))
    tier = subscription(user)['tier']
    return {'id': user.telegram_id, 'name': user.display_name, 'age': age,
            'gold': int(tier in ('gold', 'plus')), 'gold_plus': tier == 'plus',
            'silver': int(bool(user.silver_verified)), 'verified': bool(user.is_verified),
            'city': user.city, 'bio': profile.bio, 'photos': json.loads(profile.photos)}

async def eligible(s, uid, other):
    mine, target = await s.get(User, uid), await s.get(User, other)
    blocked = await s.scalar(select(BlockedUser.blocker_id).where(or_(
        (BlockedUser.blocker_id == uid) & (BlockedUser.blocked_id == other),
        (BlockedUser.blocker_id == other) & (BlockedUser.blocked_id == uid))))
    profile = await s.get(DatingProfile, other)
    if (uid == other or not target or not target.is_registered or target.is_banned or blocked
        or mine.gender not in ('male', 'female') or target.gender != ('female' if mine.gender == 'male' else 'male')
        or not profile or not json.loads(profile.photos)):
        raise HTTPException(404, 'Anketa mavjud emas.')
    return target, profile

@router.get('/api/dating/me')
async def me(uid=Depends(registered)):
    async with SessionLocal() as s:
        row = await s.get(DatingProfile, uid)
        return {'bio': row.bio if row else '', 'photos': json.loads(row.photos) if row else []}

@router.post('/api/dating/me')
async def save(body: ProfileBody, uid=Depends(registered)):
    photos = await run_in_threadpool(normalize_photos, body.photos)
    async with SessionLocal() as s:
        await s.get(User, uid, with_for_update=True)
        row = await s.get(DatingProfile, uid)
        if not row:
            row = DatingProfile(user_id=uid)
            s.add(row)
        row.bio, row.photos = body.bio.strip(), json.dumps(photos)
        await s.commit()
    return {'bio': body.bio.strip(), 'photos': photos}

@router.get('/api/dating/cards')
async def cards(uid=Depends(registered)):
    async with SessionLocal() as s:
        mine = await s.get(User, uid)
        own = await s.get(DatingProfile, uid)
        if mine.gender not in ('male', 'female') or not own or not json.loads(own.photos):
            return []
        votes = select(DatingVote.target_id).where(DatingVote.user_id == uid)
        blocked_by = select(BlockedUser.blocker_id).where(BlockedUser.blocked_id == uid)
        blocked = select(BlockedUser.blocked_id).where(BlockedUser.blocker_id == uid)
        rows = (await s.execute(select(User, DatingProfile).join(DatingProfile, DatingProfile.user_id == User.telegram_id).where(
            User.telegram_id != uid, User.is_registered.is_(True), User.is_banned.is_(False),
            User.gender == ('female' if mine.gender == 'male' else 'male'), DatingProfile.photos != '[]',
            User.telegram_id.not_in(votes), User.telegram_id.not_in(blocked), User.telegram_id.not_in(blocked_by)
        ).order_by(User.telegram_id).limit(12))).all()
        return [card(user, profile) for user, profile in rows]

@router.post('/api/dating/vote/{other}')
async def vote(other: int, body: VoteBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        # Lock both accounts in deterministic order for reciprocal concurrent likes.
        for user_id in sorted({uid, other}):
            await s.get(User, user_id, with_for_update=True)
        await eligible(s, uid, other)
        own = await s.get(DatingProfile, uid)
        if not own or not json.loads(own.photos):
            raise HTTPException(403, 'Avval anketa rasmini yuklang.')
        row = await s.get(DatingVote, (uid, other))
        if row:
            row.liked = body.liked
        else:
            s.add(DatingVote(user_id=uid, target_id=other, liked=body.liked))
        reverse = await s.get(DatingVote, (other, uid))
        matched = bool(body.liked and reverse and reverse.liked)
        await s.commit()
        return {'matched': matched}

@router.get('/api/dating/matches')
async def matches(uid=Depends(registered)):
    async with SessionLocal() as s:
        ids = (await s.scalars(select(DatingVote.target_id).where(DatingVote.user_id == uid, DatingVote.liked.is_(True)))).all()
        result = []
        for other in ids:
            reverse = await s.get(DatingVote, (other, uid))
            if not reverse or not reverse.liked:
                continue
            try:
                user, profile = await eligible(s, uid, other)
                result.append(card(user, profile))
            except HTTPException:
                continue
        return result

@router.get('/api/dating/likes')
async def likes(uid=Depends(registered)):
    async with SessionLocal() as s:
        rows = (await s.execute(select(User.telegram_id, User.display_name).join(DatingVote, DatingVote.target_id == User.telegram_id).where(DatingVote.user_id == uid, DatingVote.liked.is_(True)).order_by(User.telegram_id))).all()
        return [{'id': other, 'name': name or str(other)} for other, name in rows]

@router.post('/api/dating/undo/{other}')
async def undo_like(other: int, uid=Depends(registered)):
    async with SessionLocal() as s:
        for user_id in sorted({uid, other}):
            await s.get(User, user_id, with_for_update=True)
        row = await s.get(DatingVote, (uid, other))
        if not row:
            raise HTTPException(404, 'Bu anketa uchun qaytariladigan amal yo‘q.')
        await s.delete(row)
        await s.commit()
        return {'undone': True}

@router.get('/api/dating/history')
async def vote_history(uid=Depends(registered)):
    async with SessionLocal() as s:
        rows = (await s.execute(select(User.telegram_id, User.display_name, DatingVote.liked).join(DatingVote, DatingVote.target_id == User.telegram_id).where(DatingVote.user_id == uid).order_by(User.telegram_id))).all()
        return [{'id': other, 'name': name or str(other), 'liked': liked} for other, name, liked in rows]
