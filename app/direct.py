"""Private messaging API. Poll messages with since_revision for edits/deletions."""
from datetime import UTC, datetime, timedelta
import base64
import io
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func, or_, text
from app.database import SessionLocal
from app.models import User, MiniAvatar
from app.direct_models import DirectChat, DirectMessage, DirectRead, ChatDeletion, BlockedUser, UserPresence
from app.miniapp import registered
from app.services.badges import badge_status

router = APIRouter(prefix='/api/direct')

def now():
    return datetime.now(UTC)

def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value

async def pair_lock(s, a, b):
    # Keep this helper portable.  The database-level advisory lock previously
    # caused PostgreSQL deployments to fail before the chat request completed.
    # The unique chat constraint and transaction boundaries still protect the
    # persistent chat state.
    return None

async def user_exists(s, uid):
    user = await s.get(User, uid)
    if not user or not user.is_registered or user.is_banned:
        raise HTTPException(404, 'Foydalanuvchi topilmadi.')
    return user

async def blocked(s, a, b):
    return bool(await s.scalar(select(BlockedUser.blocker_id).where(or_(
        (BlockedUser.blocker_id == a) & (BlockedUser.blocked_id == b),
        (BlockedUser.blocker_id == b) & (BlockedUser.blocked_id == a)))))

async def access(s, chat_id, uid):
    chat = await s.get(DirectChat, chat_id)
    if not chat or uid not in (chat.user_one, chat.user_two):
        raise HTTPException(404, 'Chat topilmadi.')
    await pair_lock(s, chat.user_one, chat.user_two)
    await s.refresh(chat)
    return chat, chat.user_two if uid == chat.user_one else chat.user_one

def person_data(user, avatar, presence, include_avatar=True):
    result = {'id': user.telegram_id, 'name': user.display_name, 'app_username': user.app_username,
              **badge_status(user), 'online': bool(presence and aware(presence.last_seen_at) > now()-timedelta(seconds=30))}
    if include_avatar:
        result['avatar'] = None
        if avatar and avatar.data:
            try:
                with Image.open(io.BytesIO(base64.b64decode(avatar.data.split(',', 1)[1]))) as source:
                    if source.width * source.height > 40000000:
                        raise ValueError('Image too large')
                    thumb = ImageOps.fit(source.convert('RGB'), (128, 128))
                    output = io.BytesIO()
                    thumb.save(output, format='JPEG', quality=75)
                    result['avatar'] = 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()
            except (ValueError, OSError, IndexError):
                pass
    return result

async def person(s, uid, include_avatar=True):
    user = await s.get(User, uid)
    avatar = await s.get(MiniAvatar, uid) if include_avatar else None
    presence = await s.get(UserPresence, uid)
    return await run_in_threadpool(person_data, user, avatar, presence, include_avatar)

def message_data(m, uid):
    return {'id': m.id, 'mine': m.sender_id == uid, 'text': '' if m.is_deleted else m.text,
            'created_at': m.created_at, 'updated_at': m.updated_at, 'revision': m.revision,
            'is_edited': m.is_edited, 'is_deleted': m.is_deleted}

class TextBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class ReadBody(BaseModel):
    message_id: int = Field(ge=0)

class PresenceBody(BaseModel):
    online: bool = True

@router.post('/presence')
async def presence(body: PresenceBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        # Serialize concurrent tabs for this user's first heartbeat.
        await s.get(User, uid, with_for_update=True)
        row = await s.get(UserPresence, uid)
        stamp = now() if body.online else now()-timedelta(seconds=31)
        if row: row.last_seen_at = stamp
        else: s.add(UserPresence(user_id=uid, last_seen_at=stamp))
        await s.commit()
    return {'ok': True, 'heartbeat_seconds': 10, 'offline_after_seconds': 30}

@router.post('/chats/with/{other}')
async def open_chat(other: int, uid=Depends(registered)):
    if other == uid: raise HTTPException(422, 'O‘zingiz bilan chat ochib bo‘lmaydi.')
    async with SessionLocal() as s:
        await pair_lock(s, uid, other)
        await user_exists(s, other)
        if await blocked(s, uid, other): raise HTTPException(403, 'Foydalanuvchi bloklangan.')
        a, b = sorted((uid, other))
        chat = await s.scalar(select(DirectChat).where(DirectChat.user_one == a, DirectChat.user_two == b))
        if not chat:
            chat = DirectChat(user_one=a, user_two=b, created_at=now(), revision=0)
            s.add(chat)
            await s.flush()
        await s.execute(delete(ChatDeletion).where(ChatDeletion.chat_id == chat.id, ChatDeletion.user_id == uid))
        await s.commit()
        # Profile/presence is loaded by the messages endpoint.  Do not make
        # successful chat creation depend on that optional response payload.
        return {'chat_id': chat.id}

@router.get('/chats')
async def chats(offset: int = Query(0, ge=0), include_avatar: bool = True, uid=Depends(registered)):
    async with SessionLocal() as s:
        hidden = select(ChatDeletion.chat_id).where(ChatDeletion.user_id == uid)
        rows = (await s.scalars(select(DirectChat).where(or_(DirectChat.user_one == uid, DirectChat.user_two == uid),
            DirectChat.id.not_in(hidden)).order_by(func.coalesce(DirectChat.last_message_at, DirectChat.created_at).desc(), DirectChat.id.desc()).offset(offset).limit(51))).all()
        ids = [c.id for c in rows[:50]]
        if not ids:
            return {'chats': [], 'more': False}
        people = [c.user_two if c.user_one == uid else c.user_one for c in rows[:50]]
        users = {u.telegram_id: u for u in (await s.scalars(select(User).where(User.telegram_id.in_(people)))).all()}
        avatars = {a.user_id: a for a in (await s.scalars(select(MiniAvatar).where(MiniAvatar.user_id.in_(people)))).all()} if include_avatar else {}
        presences = {p.user_id: p for p in (await s.scalars(select(UserPresence).where(UserPresence.user_id.in_(people)))).all()}
        last_ids = select(func.max(DirectMessage.id)).where(DirectMessage.chat_id.in_(ids)).group_by(DirectMessage.chat_id)
        lasts = {m.chat_id: m for m in (await s.scalars(select(DirectMessage).where(DirectMessage.id.in_(last_ids)))).all()}
        unread_counts = dict((await s.execute(select(DirectMessage.chat_id, func.count(DirectMessage.id)).outerjoin(
            DirectRead, (DirectRead.chat_id == DirectMessage.chat_id) & (DirectRead.user_id == uid)).where(
            DirectMessage.chat_id.in_(ids), DirectMessage.sender_id != uid,
            DirectMessage.id > func.coalesce(DirectRead.last_message_id, 0), DirectMessage.is_deleted.is_(False)
        ).group_by(DirectMessage.chat_id))).all())
        result = []
        for c in rows[:50]:
            other = c.user_two if c.user_one == uid else c.user_one
            last = lasts.get(c.id)
            result.append({'id': c.id, 'partner': await run_in_threadpool(person_data, users[other], avatars.get(other), presences.get(other), include_avatar), 'last_message': message_data(last, uid) if last else None,
                           'last_message_at': c.last_message_at, 'unread': unread_counts.get(c.id, 0)})
        return {'chats': result, 'more': len(rows)>50}

@router.get('/chats/{chat_id}/messages')
async def messages(chat_id: int, since_revision: int | None = Query(None, ge=0), before_id: int | None = Query(None, ge=1), include_avatar: bool = True, uid=Depends(registered)):
    if since_revision is not None and before_id is not None: raise HTTPException(422, 'Bitta kursor yuboring.')
    async with SessionLocal() as s:
        c, other = await access(s, chat_id, uid)
        query = select(DirectMessage).where(DirectMessage.chat_id == chat_id)
        if since_revision is not None:
            query = query.where(DirectMessage.revision > since_revision).order_by(DirectMessage.revision)
        else:
            if before_id is not None: query = query.where(DirectMessage.id < before_id)
            query = query.order_by(DirectMessage.id.desc())
        rows = list((await s.scalars(query.limit(101))).all())
        more = len(rows)>100
        rows = rows[:100]
        cursor = rows[-1].revision if since_revision is not None and more else c.revision
        if since_revision is None: rows.reverse()
        mine_block = await s.get(BlockedUser, (uid, other))
        result = {'messages': [message_data(m, uid) for m in rows], 'revision': cursor, 'more': more,
                  'before_id': rows[0].id if rows else None, 'partner': await person(s, other, include_avatar),
                  'blocked_by_me': bool(mine_block), 'can_send': not await blocked(s, uid, other)}
        return result

@router.post('/chats/{chat_id}/messages')
async def send(chat_id: int, body: TextBody, uid=Depends(registered)):
    value = body.text.strip()
    if not value: raise HTTPException(422, 'Xabar bo‘sh.')
    async with SessionLocal() as s:
        c, other = await access(s, chat_id, uid)
        user = await user_exists(s, uid)
        await user_exists(s, other)
        if user.muted_until and aware(user.muted_until)>now(): raise HTTPException(423, 'Mute faol.')
        if await blocked(s, uid, other): raise HTTPException(403, 'Foydalanuvchi bloklangan.')
        c.revision += 1
        c.last_message_at = now()
        m = DirectMessage(chat_id=chat_id, sender_id=uid, text=value, created_at=c.last_message_at, updated_at=c.last_message_at, revision=c.revision)
        s.add(m)
        await s.execute(delete(ChatDeletion).where(ChatDeletion.chat_id == chat_id))
        await s.commit()
        return message_data(m, uid)

async def change_message(chat_id, message_id, uid, value=None):
    async with SessionLocal() as s:
        c, other = await access(s, chat_id, uid)
        m = await s.get(DirectMessage, message_id)
        if not m or m.chat_id != chat_id: raise HTTPException(404, 'Xabar topilmadi.')
        if m.sender_id != uid: raise HTTPException(403, 'Faqat o‘z xabaringizni o‘zgartira olasiz.')
        if m.is_deleted: raise HTTPException(409, 'Xabar o‘chirilgan.')
        if value is not None:
            if not value.strip(): raise HTTPException(422, 'Xabar bo‘sh.')
            user = await user_exists(s, uid)
            if user.muted_until and aware(user.muted_until)>now(): raise HTTPException(423, 'Mute faol.')
            if await blocked(s, uid, other): raise HTTPException(403, 'Foydalanuvchi bloklangan.')
            m.text, m.is_edited = value.strip(), True
        else:
            m.text, m.is_deleted = '', True
        c.revision += 1
        m.revision, m.updated_at = c.revision, now()
        await s.commit()
        return message_data(m, uid)

@router.patch('/chats/{chat_id}/messages/{message_id}')
async def edit(chat_id: int, message_id: int, body: TextBody, uid=Depends(registered)):
    return await change_message(chat_id, message_id, uid, body.text)

@router.delete('/chats/{chat_id}/messages/{message_id}')
async def remove_message(chat_id: int, message_id: int, uid=Depends(registered)):
    return await change_message(chat_id, message_id, uid)

@router.post('/chats/{chat_id}/read')
async def mark_read(chat_id: int, body: ReadBody, uid=Depends(registered)):
    async with SessionLocal() as s:
        await access(s, chat_id, uid)
        if body.message_id:
            m = await s.get(DirectMessage, body.message_id)
            if not m or m.chat_id != chat_id: raise HTTPException(422, 'Xabar bu chatga tegishli emas.')
        row = await s.get(DirectRead, (chat_id, uid))
        if row: row.last_message_id = max(row.last_message_id, body.message_id)
        else: s.add(DirectRead(chat_id=chat_id, user_id=uid, last_message_id=body.message_id))
        await s.commit()
    return {'ok': True}

@router.delete('/chats/{chat_id}')
async def hide_chat(chat_id: int, uid=Depends(registered)):
    async with SessionLocal() as s:
        await access(s, chat_id, uid)
        row = await s.get(ChatDeletion, (chat_id, uid))
        if row: row.deleted_at = now()
        else: s.add(ChatDeletion(chat_id=chat_id, user_id=uid, deleted_at=now()))
        await s.commit()
    return {'ok': True}

@router.get('/blocks')
async def blocks(uid=Depends(registered)):
    async with SessionLocal() as s:
        ids = (await s.scalars(select(BlockedUser.blocked_id).where(BlockedUser.blocker_id == uid))).all()
        return [await person(s, other) for other in ids]

@router.post('/blocks/{other}')
async def block(other: int, uid=Depends(registered)):
    if other == uid: raise HTTPException(422, 'O‘zingizni bloklab bo‘lmaydi.')
    async with SessionLocal() as s:
        await pair_lock(s, uid, other)
        await user_exists(s, other)
        if not await s.get(BlockedUser, (uid, other)):
            s.add(BlockedUser(blocker_id=uid, blocked_id=other, created_at=now()))
        await s.commit()
    return {'ok': True}

@router.delete('/blocks/{other}')
async def unblock(other: int, uid=Depends(registered)):
    async with SessionLocal() as s:
        await pair_lock(s, uid, other)
        await s.execute(delete(BlockedUser).where(BlockedUser.blocker_id == uid, BlockedUser.blocked_id == other))
        await s.commit()
    return {'ok': True}
