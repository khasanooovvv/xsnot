import base64
import hashlib
import hmac
import io
import json
import time
import secrets
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool
register_heif_opener()
from sqlalchemy import select, func, delete, update, text as sql, or_
from app.config import settings
from app.services.badges import badge_status
from app.services.referral_notifications import send_invite_link
from app.database import SessionLocal
from app.models import User, Match, MatchQueue, MiniAvatar, MiniMessage, Report, ReferralShare, ReferralHistory, VideoVerification, ChatInvitation
from app.services.users import get_or_create, age_on, days_left, apply_referral_reward, referral_count, consume_share
from app.services.matching import active_match, find_or_queue, end_match, leave_queue, is_anonymous, set_anonymous

router = APIRouter()

@router.get('/assets/gold-status.js')
async def gold_status_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'gold-status.js', media_type='application/javascript')

@router.get('/assets/roulette.js')
async def roulette_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'roulette.js', media_type='application/javascript')

@router.get('/assets/profile-editor.js')
async def profile_editor_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'profile-editor.js', media_type='application/javascript')

@router.get('/assets/partner-profile.js')
async def partner_profile_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'partner-profile.js', media_type='application/javascript')

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

@router.get('/assets/theme.css')
async def theme_styles():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'theme.css', media_type='text/css')

@router.get('/assets/theme.js')
async def theme_script():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'theme.js', media_type='application/javascript')

@router.get('/assets/chat-media.css')
async def chat_media_styles():
    return FileResponse(Path(__file__).parent / 'web' / 'assets' / 'chat-media.css', media_type='text/css')

@router.get('/')
async def index():
    return FileResponse(Path(__file__).parent / 'web' / 'index.html', headers={'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'})

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

async def profile(s, u, include_avatar=True, include_referrals=True):
    avatar = await s.get(MiniAvatar, u.telegram_id) if include_avatar else None
    return dict(id=u.telegram_id, name=u.display_name, language=u.language, city=u.city, age=age_on(u.birth_date) if u.birth_date else None,
        archive_consent=bool(u.archive_consent_at), app_username=u.app_username, bio=u.bio or '',
        registered=u.is_registered, **badge_status(u),
        invite_limit=settings().silver_referral_daily_share_limit if u.silver_verified else settings().referral_daily_share_limit,
        referrals=await referral_count(s, u.telegram_id) if include_referrals else 0, avatar=avatar.data if avatar else None)

@router.get('/api/me')
async def me(include_avatar: bool = True, uid=Depends(identity)):
    async with SessionLocal() as s:
        user = await s.get(User, uid)
        data = await profile(s, user, include_avatar)
        data['muted_until'] = user.muted_until
        data['birthday'] = user.birth_date
        data['gender'] = user.gender
        data['server_now'] = datetime.now(UTC)
        return data

@router.get('/api/me/avatar')
async def my_avatar(version: str = '', uid=Depends(identity)):
    async with SessionLocal() as s:
        avatar = await s.get(MiniAvatar, uid)
        data = avatar.data if avatar else None
        current = hashlib.sha256(data.encode()).hexdigest() if data else 'none'
        if version == current:
            return {'version': current, 'unchanged': True}
        return {'avatar': data, 'version': current, 'unchanged': False}

@router.get('/api/me/gold')
async def my_gold(uid=Depends(registered)):
    async with SessionLocal() as s:
        user = await s.get(User, uid)
        until = user.gold_until
        if until and until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
        return {'gold_until': until, 'server_now': datetime.now(UTC)}

@router.post('/api/delete-account')
async def delete_account(uid=Depends(identity)):
    """Permanently erase every record owned by the authenticated account."""
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730022)'))
        user = await s.get(User, uid, with_for_update=True)
        if not user:
            return {'ok': True, 'deleted': False}
        current = await active_match(s, uid)
        if current:
            await end_match(s, current)
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
        # Keep an inactive ledger so the same Telegram account cannot earn a
        # referral again after deleting and recreating its profile.
        await s.execute(update(ReferralHistory).where(ReferralHistory.referrer_id == uid).values(active=False))
        user.gold_until = None
        user.premium_until = None
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

class ProfileEdit(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    app_username: str | None = Field(default=None, max_length=25)
    bio: str | None = Field(default=None, max_length=300)
    avatar: str | None = Field(default=None, max_length=2000000)

@router.post('/api/profile')
async def edit_profile(body: ProfileEdit, uid=Depends(registered)):
    name = body.name.strip()
    if len(name) < 2:
        raise HTTPException(422, 'Ism kamida 2 ta belgidan iborat bo‘lsin.')
    handle = body.app_username.strip().removeprefix('@').lower() if body.app_username is not None else None
    if handle and not re.fullmatch(r'[a-z][a-z0-9_]{2,23}', handle):
        raise HTTPException(422, 'Username 3–24 ta lotin harfi, raqam yoki _ dan iborat bo‘lsin va harf bilan boshlansin.')
    avatar = None
    if body.avatar is not None:
        try:
            raw = base64.b64decode(body.avatar.split(',', 1)[1], validate=True)
            with Image.open(io.BytesIO(raw)) as source:
                if source.width * source.height > 40000000:
                    raise ValueError()
                image = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (512, 512))
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=90)
                avatar = 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()
        except Exception:
            raise HTTPException(422, 'Rasm ochilmadi. Boshqa rasm tanlang.')
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730023)'))
        if handle:
            owner = await s.scalar(select(User.telegram_id).where(User.app_username == handle))
            if owner is not None and owner != uid:
                raise HTTPException(409, 'Bu username band. Boshqasini tanlang.')
        user = await s.get(User, uid, with_for_update=True)
        user.display_name = name
        if body.app_username is not None:
            user.app_username = handle or None
        if body.bio is not None:
            user.bio = body.bio.strip()
        if avatar:
            existing = await s.get(MiniAvatar, uid)
            if existing:
                existing.data = avatar
            else:
                s.add(MiniAvatar(user_id=uid, data=avatar))
        await s.commit()
        data = await profile(s, user)
        data.update(birthday=user.birth_date, gender=user.gender)
        return data

class Registration(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    gender: Literal['male', 'female']
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
        u.display_name, u.gender, u.birth_date, u.city = body.name.strip(), body.gender, body.birthday, body.city.strip()
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
    accepted: Literal[True]
    archive_consent: bool = False
    roulette: bool = False

class PrivacyChoice(BaseModel):
    anonymous: bool

@router.post('/api/chat/privacy')
async def chat_privacy(body: PrivacyChoice, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        queued = await s.get(MatchQueue, uid)
        if queued and queued.mode.startswith('mini_'):
            queued.mode = ('mini_ra' if body.anonymous else 'mini_ro') if queued.mode in ('mini_ra', 'mini_ro') else ('mini_anonymous' if body.anonymous else 'mini_open')
        m = await active_match(s, uid)
        if m and m.mode.startswith('mini_'):
            set_anonymous(m, uid, body.anonymous)
        await s.commit()
    return {'ok': True}

@router.post('/api/search')
async def search(body: Search, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        user = await s.get(User, uid, with_for_update=True)
        if settings().archive_channel_id and not user.archive_consent_at and not body.archive_consent:
            raise HTTPException(422, 'Chat qoidalariga rozilik bering.')
        if body.archive_consent and not user.archive_consent_at:
            user.archive_consent_at = datetime.now(UTC)
        archive_consent = bool(user.archive_consent_at)
        await s.execute(delete(MatchQueue).where(MatchQueue.mode.in_(['mini_anonymous', 'mini_open', 'mini_ra', 'mini_ro']), MatchQueue.queued_at < datetime.now(UTC) - timedelta(seconds=30)))
        existing = await active_match(s, uid)
        if existing and existing.mode.startswith('mini_'):
            set_anonymous(existing, uid, body.mode == 'anonymous')
        elif not existing:
            if body.roulette:
                await leave_queue(s, uid)
                s.add(MatchQueue(user_id=uid, mode='mini_ra' if body.mode == 'anonymous' else 'mini_ro', archive_consent=archive_consent))
            else:
                await find_or_queue(s, user, 'mini_' + body.mode, None, None, None, archive_consent=archive_consent)
        await s.commit()
    return {'ok': True}

def roulette_ticket(uid, candidate, expires):
    # Opaque, viewer-bound selection: no Telegram IDs are sent to the browser.
    payload = f'roulette:{uid}:{candidate.user_id}:{candidate.mode}:{expires}'
    signature = hmac.new(settings().bot_token.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f'{expires}.{signature}'

async def roulette_candidates(s, uid):
    busy = select(Match.user_one_id).where(Match.status == 'active').union(select(Match.user_two_id).where(Match.status == 'active'))
    reserved = select(ChatInvitation.sender_id).where(ChatInvitation.expires_at > datetime.now(UTC)).union(select(ChatInvitation.recipient_id).where(ChatInvitation.expires_at > datetime.now(UTC)))
    return (await s.scalars(select(MatchQueue).join(User, User.telegram_id == MatchQueue.user_id).where(
        MatchQueue.user_id != uid, MatchQueue.mode.in_(['mini_ra', 'mini_ro']),
        MatchQueue.queued_at >= datetime.now(UTC) - timedelta(seconds=30),
        User.is_registered.is_(True), User.is_banned.is_(False),
        MatchQueue.user_id.not_in(busy),
        MatchQueue.user_id.not_in(reserved),
    ))).all()

async def pending_invitation(s, uid):
    return await s.scalar(select(ChatInvitation).where(
        or_(ChatInvitation.sender_id == uid, ChatInvitation.recipient_id == uid),
        ChatInvitation.expires_at > datetime.now(UTC)))

async def invitation_payload(s, invitation, uid):
    incoming = invitation.recipient_id == uid
    other = invitation.sender_id if incoming else invitation.recipient_id
    queued = await s.get(MatchQueue, other)
    user = await s.get(User, other)
    if (not queued or queued.mode not in ('mini_ra', 'mini_ro') or
        queued.queued_at < datetime.now(UTC) - timedelta(seconds=30) or
        not user or not user.is_registered or user.is_banned or await active_match(s, other)):
        await s.delete(invitation)
        return None
    person = {'name': 'Anonim', 'avatar': None, 'anonymous': True}
    if queued.mode == 'mini_ro':
        data = await profile(s, user, include_referrals=False)
        person = {key: data[key] for key in ('name', 'avatar')}
        person['anonymous'] = False
    return {'id': invitation.id, 'direction': 'incoming' if incoming else 'outgoing',
            'expires_at': invitation.expires_at.timestamp(), 'remaining': max(0, int((invitation.expires_at - datetime.now(UTC)).total_seconds())), 'person': person}

@router.post('/api/roulette/spin')
async def roulette_spin(uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        own = await s.get(MatchQueue, uid)
        if not own or own.mode not in ('mini_ra', 'mini_ro') or await active_match(s, uid):
            raise HTTPException(409, 'Qidiruvni qayta boshlang.')
        if await pending_invitation(s, uid):
            raise HTTPException(409, 'Avval joriy taklifga javob bering yoki uni bekor qiling.')
        own.queued_at = datetime.now(UTC)
        candidates = [c for c in await roulette_candidates(s, uid) if not settings().archive_channel_id or (own.archive_consent and c.archive_consent)]
        secrets.SystemRandom().shuffle(candidates)
        candidates = candidates[:12]
        items = []
        for candidate in candidates:
            item = {'name': 'Anonim', 'avatar': None, 'anonymous': True}
            if candidate.mode == 'mini_ro':
                p = await profile(s, await s.get(User, candidate.user_id), include_referrals=False)
                item = {k: p[k] for k in ('name', 'avatar')}
                item['anonymous'] = False
            items.append(item)
        await s.commit()
        return {'items': items, 'selected': 0 if items else None,
                'ticket': roulette_ticket(uid, candidates[0], int(time.time()) + 90) if items else None}

class RouletteChoice(BaseModel):
    ticket: str = Field(max_length=100)

@router.post('/api/roulette/choose')
async def roulette_choose(body: RouletteChoice, uid=Depends(registered)):
    try:
        expires = int(body.ticket.split('.', 1)[0])
        if not time.time() < expires <= time.time() + 91:
            raise ValueError()
    except ValueError:
        raise HTTPException(409, 'Tanlov eskirdi. Qayta aylantiring.')
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        own = await s.get(MatchQueue, uid)
        if not own or own.mode not in ('mini_ra', 'mini_ro') or await active_match(s, uid):
            raise HTTPException(409, 'Qidiruvni qayta boshlang.')
        if await pending_invitation(s, uid):
            raise HTTPException(409, 'Sizda javob kutilayotgan taklif bor.')
        candidates = await roulette_candidates(s, uid)
        partner = next((c for c in candidates if hmac.compare_digest(body.ticket, roulette_ticket(uid, c, expires))), None)
        if not partner or (settings().archive_channel_id and not (own.archive_consent and partner.archive_consent)):
            raise HTTPException(409, 'Bu suhbatdosh hozir band. Qayta aylantiring.')
        await s.execute(delete(ChatInvitation).where(ChatInvitation.expires_at <= datetime.now(UTC)))
        invitation = ChatInvitation(id=secrets.token_urlsafe(18), sender_id=uid, recipient_id=partner.user_id,
                                    expires_at=datetime.now(UTC) + timedelta(seconds=30))
        s.add(invitation)
        own.queued_at = datetime.now(UTC)
        payload = await invitation_payload(s, invitation, uid)
        if payload is None:
            raise HTTPException(409, 'Bu suhbatdosh hozir band. Qayta aylantiring.')
        await s.commit()
    return {'ok': True, 'invitation': payload}

class InvitationResponse(BaseModel):
    invitation_id: str = Field(min_length=1, max_length=36)
    action: Literal['accept', 'reject', 'cancel']

@router.post('/api/roulette/respond')
async def respond_invitation(body: InvitationResponse, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        invitation = await s.get(ChatInvitation, body.invitation_id)
        if not invitation or uid not in (invitation.sender_id, invitation.recipient_id):
            raise HTTPException(409, 'Taklif endi mavjud emas.')
        allowed = ('cancel',) if uid == invitation.sender_id else ('accept', 'reject')
        if body.action not in allowed:
            raise HTTPException(403, 'Bu taklifni tasdiqlay olmaysiz.')
        if body.action != 'accept':
            await s.delete(invitation)
            await s.commit()
            return {'ok': True}
        if invitation.expires_at <= datetime.now(UTC):
            raise HTTPException(409, 'Taklif muddati tugadi. Qayta aylantiring.')
        sender = await s.get(MatchQueue, invitation.sender_id)
        recipient = await s.get(MatchQueue, invitation.recipient_id)
        for queued, participant in ((sender, invitation.sender_id), (recipient, invitation.recipient_id)):
            user = await s.get(User, participant)
            if (not queued or queued.mode not in ('mini_ra', 'mini_ro') or
                queued.queued_at < datetime.now(UTC) - timedelta(seconds=30) or
                not user or not user.is_registered or user.is_banned or await active_match(s, participant)):
                raise HTTPException(409, 'Suhbatdosh qidiruvdan chiqdi. Qayta aylantiring.')
        if settings().archive_channel_id and not (sender.archive_consent and recipient.archive_consent):
            raise HTTPException(409, 'Suhbatni boshlash uchun qoidalarga rozilik kerak.')
        s.add(Match(user_one_id=invitation.sender_id, user_two_id=invitation.recipient_id,
                    mode='mini_' + ('a' if sender.mode == 'mini_ra' else 'o') + ('a' if recipient.mode == 'mini_ra' else 'o'),
                    archive_consent=bool(sender.archive_consent and recipient.archive_consent)))
        await leave_queue(s, invitation.sender_id)
        await leave_queue(s, invitation.recipient_id)
        await s.commit()
        return {'ok': True}

@router.get('/api/chat')
async def chat(after: int = 0, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730020)'))
        m = await active_match(s, uid)
        if not m or not m.mode.startswith('mini_'):
            queued = await s.get(MatchQueue, uid)
            if queued and queued.mode.startswith('mini_'):
                queued.queued_at = datetime.now(UTC)
                invitation = await pending_invitation(s, uid)
                payload = await invitation_payload(s, invitation, uid) if invitation else None
                await s.commit()
                return {'status': 'searching', 'invitation': payload}
            return {'status': 'idle'}
        partner_id = m.user_two_id if m.user_one_id == uid else m.user_one_id
        partner = {'name': 'Anonim', 'avatar': None, 'anonymous': True}
        if not is_anonymous(m, partner_id):
            p = await profile(s, await s.get(User, partner_id), include_referrals=False)
            partner = {k:p[k] for k in ('name', 'avatar', 'age', 'city', 'verified', 'silver', 'gold')}
            partner['anonymous'] = False
        rows = (await s.scalars(select(MiniMessage).where(MiniMessage.match_id == m.id, MiniMessage.id > after).order_by(MiniMessage.id).limit(100))).all()
        messages = []
        for r in rows:
            item = {'id': r.id, 'mine': r.sender_id == uid, 'text': r.text}
            if r.image_data and r.image_type:
                item['image'] = 'data:' + r.image_type + ';base64,' + base64.b64encode(r.image_data).decode()
                item['image_name'] = r.image_name
            messages.append(item)
        return {'status': 'active', 'match': m.id, 'partner': partner, 'own_anonymous': is_anonymous(m, uid), 'messages': messages}

@router.get('/api/chat/partner')
async def partner_profile(match_id: int, uid=Depends(registered)):
    async with SessionLocal() as s:
        m = await active_match(s, uid)
        if not m or m.id != match_id or not m.mode.startswith('mini_'):
            raise HTTPException(409, 'Suhbat tugagan. Profilni ochib bo‘lmaydi.')
        partner_id = m.user_two_id if m.user_one_id == uid else m.user_one_id
        if is_anonymous(m, partner_id):
            return {'match': m.id, 'partner': {'name': 'Anonim', 'avatar': None, 'anonymous': True}}
        user = await s.get(User, partner_id)
        if not user or not user.is_registered or user.is_banned:
            raise HTTPException(404, 'Profil mavjud emas.')
        data = await profile(s, user, include_referrals=False)
        public = {key: data[key] for key in ('name', 'avatar', 'app_username', 'bio', 'age', 'city', 'verified', 'silver', 'gold')}
        public['anonymous'] = False
        return {'match': m.id, 'partner': public}

class MessageBody(BaseModel):
    match: int
    text: str = Field(min_length=1, max_length=2000)

async def _check_message_access(s, uid, match_id):
    user = await s.get(User, uid)
    if user.muted_until:
        until = user.muted_until.replace(tzinfo=UTC) if user.muted_until.tzinfo is None else user.muted_until
        if until > datetime.now(UTC):
            raise HTTPException(423, f'Mute: {until.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")} gacha xabar yubora olmaysiz.')
    m = await active_match(s, uid)
    if not m or m.id != match_id or not m.mode.startswith('mini_'):
        raise HTTPException(409, 'Suhbat tugagan.')
    return m

@router.post('/api/message')
async def message(body: MessageBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        m = await _check_message_access(s, uid, body.match)
        if not body.text.strip(): raise HTTPException(422, 'Xabar bo‘sh.')
        item = MiniMessage(match_id=m.id, sender_id=uid, text=body.text.strip())
        s.add(item)
        await s.commit()
    return {'ok': True, 'id': item.id}

@router.post('/api/message/image')
async def image_message(match: int = Form(...), image: UploadFile = File(...), uid=Depends(registered)):
    filename = (image.filename or 'image').strip()[:255]
    suffix = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    image_type = image.content_type.lower() if image.content_type and image.content_type.startswith('image/') else ({'heic': 'image/heic', 'heif': 'image/heif'}.get(suffix) or '')
    if not image_type:
        raise HTTPException(422, 'Faqat rasm yuborish mumkin.')
    try:
        content = await image.read(10 * 1024 * 1024 + 1)
    finally:
        await image.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(422, 'Rasm 10 MB dan kichik bo‘lishi kerak.')
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.verify()
    except Exception:
        raise HTTPException(422, 'Rasmni ochib bo‘lmadi.')
    async with SessionLocal() as s:
        m = await _check_message_access(s, uid, match)
        item = MiniMessage(match_id=m.id, sender_id=uid, text='', image_data=content,
                           image_type=image_type, image_name=filename)
        s.add(item)
        await s.commit()
    return {'ok': True, 'id': item.id}

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
        rows = (await s.execute(select(User, func.count(ReferralHistory.id)).join(ReferralHistory, ReferralHistory.referrer_id == User.telegram_id).where(ReferralHistory.active.is_(True)).group_by(User.telegram_id, User.display_name).order_by(func.count(ReferralHistory.id).desc(), User.telegram_id).limit(10))).all()
        return [{'name':u.display_name, 'count':count, **badge_status(u)} for u, count in rows]

@router.post('/api/invite')
async def invite(request: Request, uid=Depends(registered)):
    async with SessionLocal() as s:
        await s.execute(sql('SELECT pg_advisory_xact_lock(730019)'))
        language = (await s.get(User, uid)).language
        await s.commit()
    link = f'https://t.me/{settings().public_bot_username.lstrip("@")}?start=ref_{uid}'
    sent = await send_invite_link(getattr(request.app.state, 'bot', None), uid, link, language)
    return {'url': link, 'bot_sent': sent}
