"""Consented Mini App archives, delivered from a durable transactional outbox."""
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy import delete, func, select
from app.config import settings
from app.database import SessionLocal
from app.models import ArchiveDelivery, MiniMessage, User

log = logging.getLogger(__name__)

def identity_label(user):
    name = ' '.join((user.display_name or 'Nomsiz').split())
    handle = '@' + user.username.lstrip('@') if user.username else 'ID: ' + str(user.telegram_id)
    return f'{name} | {handle}'

def chat_text(match, people, messages, part):
    header = (f'Suhbat #{match.id} — {part}-qism\n'
              f'1. {identity_label(people[0])}\n2. {identity_label(people[1])}\n'
              f'Boshlangan: {match.started_at}\nTugagan: {match.ended_at}\nVaqt zonasi: UTC\n\n')
    names = {u.telegram_id: identity_label(u) for u in people}
    lines = [header]
    for m in messages:
        who = names.get(m.sender_id, f'ID: {m.sender_id}')
        lines.append(f'[{m.id}] {who}\n    ' + m.text.replace('\n', '\n    ') + '\n\n')
    return ''.join(lines).encode('utf-8')

async def enqueue_chat(session, match):
    channel = settings().archive_channel_id.strip()
    if not channel or not match.mode.startswith('mini_') or not match.archive_consent:
        return
    if await session.scalar(select(ArchiveDelivery.id).where(ArchiveDelivery.event_key == f'chat:{match.id}:1')):
        return
    people = [await session.get(User, uid) for uid in (match.user_one_id, match.user_two_id)]
    if not all(people):
        return
    caption = f'Suhbat #{match.id}\n1. {identity_label(people[0])}\n2. {identity_label(people[1])}'
    # Bounded batches keep each ZIP safely below Telegram's upload limit.
    cursor, part = 0, 1
    while True:
        rows = (await session.scalars(select(MiniMessage).where(MiniMessage.match_id == match.id, MiniMessage.id > cursor).order_by(MiniMessage.id).limit(1000))).all()
        if not rows and part > 1:
            break
        payload = await asyncio.to_thread(chat_text, match, people, rows, part)
        session.add(ArchiveDelivery(event_key=f'chat:{match.id}:{part}', channel_id=channel, media_type='text/plain', filename=f'chat_{match.id}_{part}.txt', caption=caption+f'\nQism: {part}', payload=payload))
        if len(rows) < 1000:
            break
        cursor, part = rows[-1].id, part + 1

def enqueue_video(session, user, content, media_type, submitted_at):
    channel = settings().archive_channel_id.strip()
    if not channel:
        return
    event = submitted_at.strftime('%Y%m%dT%H%M%S%f')
    suffix = 'mp4' if media_type == 'video/mp4' else 'webm'
    session.add(ArchiveDelivery(event_key=f'verification:{user.telegram_id}:{event}', channel_id=channel, media_type=media_type,
        filename=f'verification_{user.telegram_id}_{event}.{suffix}',
        caption=f'Verifikatsiya\n{identity_label(user)}\nYuborilgan: {submitted_at.isoformat()} (UTC)', payload=content))

async def send_delivery(bot, row):
    channel = int(row.channel_id) if row.channel_id.lstrip('-').isdigit() else row.channel_id
    upload = BufferedInputFile(row.payload, filename=row.filename)
    options = dict(chat_id=channel, caption=row.caption, parse_mode=None, protect_content=True, request_timeout=60)
    if row.media_type == 'video/mp4':
        return await bot.send_video(video=upload, **options)
    return await bot.send_document(document=upload, **options)

async def send_video_immediately(bot, channel_id, caption, content, media_type, filename):
    """Send a fresh verification video without making the user wait for the outbox."""
    if not bot or not channel_id:
        return
    channel = int(channel_id) if channel_id.lstrip('-').isdigit() else channel_id
    upload = BufferedInputFile(content, filename=filename)
    options = dict(chat_id=channel, caption=caption, parse_mode=None, protect_content=True, request_timeout=60)
    try:
        if media_type == 'video/mp4':
            await bot.send_video(video=upload, **options)
        else:
            await bot.send_document(document=upload, **options)
    except Exception as error:
        log.warning('Immediate archive delivery failed (%s)', type(error).__name__)

async def deliver_one(bot):
    async with SessionLocal() as session:
        row = await session.scalar(select(ArchiveDelivery).where(ArchiveDelivery.sent_at.is_(None), ArchiveDelivery.next_attempt_at <= datetime.now(UTC)).order_by(ArchiveDelivery.id).with_for_update(skip_locked=True).limit(1))
        if row is None:
            return False
        try:
            result = await send_delivery(bot, row)
            event_key = row.event_key
            row.message_id = result.message_id
            row.sent_at = datetime.now(UTC)
            row.payload = None
            if event_key.startswith('chat:'):
                match_id_text = event_key.split(':', 2)[1]
                if match_id_text.isdigit():
                    prefix = f'chat:{match_id_text}:'
                    pending = await session.scalar(select(func.count(ArchiveDelivery.id)).where(ArchiveDelivery.event_key.like(prefix + '%'), ArchiveDelivery.sent_at.is_(None)))
                    if not pending:
                        await session.execute(delete(MiniMessage).where(MiniMessage.match_id == int(match_id_text)))
                        await session.execute(delete(ArchiveDelivery).where(ArchiveDelivery.event_key.like(prefix + '%')))
            elif event_key.startswith('verification:'):
                await session.delete(row)
        except Exception as error:
            row.attempts += 1
            delay = error.retry_after if isinstance(error, TelegramRetryAfter) else min(3600, 10 * 2 ** min(row.attempts, 8))
            row.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
            log.warning('Archive delivery %s failed (%s); retry scheduled', row.id, type(error).__name__)
        await session.commit()
    return True

async def archive_worker(bot):
    while True:
        try:
            sent = await deliver_one(bot)
        except Exception as error:
            log.warning('Archive worker failed (%s)', type(error).__name__)
            sent = False
        await asyncio.sleep(1 if sent else 5)
