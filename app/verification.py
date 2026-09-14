"""Private video submissions and human review, with no automated sex inference."""
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import defer
from app.database import SessionLocal
from app.models import User, MiniAvatar, VideoVerification
from app.miniapp import registered
from app.services.referral_notifications import send_verification_result
from app.services.archive import enqueue_video
from app.config import settings

router = APIRouter(prefix='/api/verification')
admin_router = APIRouter(prefix='/admin/verifications')
MAX_VIDEO_BYTES = 15 * 1024 * 1024

@router.get('')
async def verification_status(uid=Depends(registered)):
    async with SessionLocal() as s:
        u = await s.get(User, uid)
        silver_verified = bool(getattr(u, 'silver_verified', False))
        if silver_verified:
            return {'status': 'approved', 'reason': None}
        # Do not make the profile screen depend on the verification table being
        # present during a rolling deploy or on an older database.
        return {'status': 'none', 'reason': None}

@router.post('/submit')
async def submit(video: UploadFile = File(...), consent: bool = Form(...), archive_consent: bool = Form(False), uid=Depends(registered)):
    if not consent: raise HTTPException(422, 'Videoni admin ko‘rishiga rozilik kerak.')
    try:
        content = await video.read(MAX_VIDEO_BYTES + 1)
    finally:
        await video.close()
    if len(content) > MAX_VIDEO_BYTES or len(content) < 16:
        raise HTTPException(422, 'Video 15 MB dan kichik bo‘lishi kerak.')
    if content[4:8] == b'ftyp': media = 'video/mp4'
    elif content[:4] == b'\x1a\x45\xdf\xa3': media = 'video/webm'
    else: raise HTTPException(422, 'MP4 yoki WebM video yuboring.')
    async with SessionLocal() as s:
        u = await s.get(User, uid, with_for_update=True)
        if settings().archive_channel_id and not u.archive_consent_at and not archive_consent:
            raise HTTPException(422, 'Arxivlash qoidalariga rozilik bering.')
        if archive_consent and not u.archive_consent_at:
            u.archive_consent_at = datetime.now(UTC)
        archive_consent = bool(u.archive_consent_at)
        row = await s.get(VideoVerification, uid)
        if u.silver_verified:
            raise HTTPException(409, 'Silver allaqachon tasdiqlangan.')
        if row and row.status == 'pending':
            raise HTTPException(409, 'Video admin tekshiruvida.')
        if not row:
            # Legacy non-null columns retained for existing deployments; no code is required.
            row = VideoVerification(user_id=uid, challenge='', challenge_until=datetime.now(UTC))
            s.add(row)
        row.video, row.media_type, row.status = content, media, 'pending'
        row.submitted_at = row.consent_at = datetime.now(UTC)
        row.reviewed_at, row.reason = None, None
        if archive_consent:
            enqueue_video(s, u, content, media, row.submitted_at)
        await s.commit()
    return {'status':'pending'}

@admin_router.get('')
async def pending_verifications():
    async with SessionLocal() as s:
        rows = (await s.execute(select(VideoVerification.user_id, VideoVerification.submitted_at, User.display_name).join(User, User.telegram_id == VideoVerification.user_id).where(VideoVerification.status == 'pending').order_by(VideoVerification.submitted_at).limit(50))).all()
        return [{'id':r.user_id,'name':r.display_name,'at':r.submitted_at} for r in rows]

@admin_router.get('/{uid}/profile')
async def review_profile(uid: int):
    async with SessionLocal() as s:
        u = await s.get(User, uid)
        if not u: raise HTTPException(404, 'User not found')
        avatar = await s.get(MiniAvatar, uid)
        return {'name':u.display_name,'avatar':avatar.data if avatar else None,'city':u.city}

@admin_router.get('/{uid}/video')
async def review_video(uid: int, range_header: str | None = Header(default=None, alias='Range')):
    async with SessionLocal() as s:
        row = await s.get(VideoVerification, uid)
        if not row or row.status != 'pending' or not row.video: raise HTTPException(404, 'Video topilmadi.')
        data, media = row.video, row.media_type
    headers = {'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff','Accept-Ranges':'bytes'}
    if range_header:
        try:
            unit, bounds = range_header.split('=',1)
            first,last = bounds.split('-',1)
            if unit != 'bytes' or ',' in bounds: raise ValueError()
            start = int(first) if first else max(0,len(data)-int(last))
            end = min(int(last),len(data)-1) if last and first else len(data)-1
            if not 0 <= start <= end < len(data): raise ValueError()
        except ValueError:
            return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{len(data)}'})
        headers['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
        return Response(data[start:end+1],status_code=206,media_type=media,headers=headers)
    return Response(data,media_type=media,headers=headers)

class Decision(BaseModel):
    approved: bool
    reason: str = Field(default='',max_length=500)

@admin_router.post('/{uid}/review')
async def review(request: Request, uid: int, body: Decision):
    if not body.approved and not body.reason.strip(): raise HTTPException(422, 'Rad etish sababini yozing.')
    async with SessionLocal() as s:
        u = await s.get(User, uid, with_for_update=True)
        row = await s.get(VideoVerification, uid, with_for_update=True)
        if not u or not row or row.status != 'pending': raise HTTPException(409, 'Bu video allaqachon ko‘rib chiqilgan.')
        row.status = 'approved' if body.approved else 'rejected'
        row.reason = None if body.approved else body.reason.strip()
        row.reviewed_at = datetime.now(UTC)
        row.video, row.media_type = None, None
        u.silver_verified = body.approved
        language = u.language
        await s.commit()
    await send_verification_result(getattr(request.app.state, 'bot', None), uid, body.approved, body.reason.strip(), language)
    return {'status':row.status}
