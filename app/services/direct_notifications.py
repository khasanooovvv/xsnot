"""Telegram notification linking to an authorized private conversation."""
import asyncio
import logging
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.exceptions import TelegramAPIError
from app.config import settings

async def notify_direct_message(bot, recipient, chat_id, name, username, language):
    base = settings().webapp_url
    if bot is None or not base:
        return
    url = urlsplit(base)
    params = dict(parse_qsl(url.query))
    params['dm_chat'] = str(chat_id)
    target = urlunsplit((url.scheme, url.netloc, url.path, urlencode(params), url.fragment))
    sender = name
    text, label = {
        'uz': (f'💬 {sender} sizga xabar yozdi.', '📩 Xabarni o‘qish'),
        'ru': (f'💬 {sender} написал(а) вам.', '📩 Прочитать сообщение'),
        'en': (f'💬 {sender} sent you a message.', '📩 Read message'),
    }.get(language, (f'💬 {sender} sizga xabar yozdi.', '📩 Xabarni o‘qish'))
    try:
        await bot.send_message(recipient, text, parse_mode=None,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=label, web_app=WebAppInfo(url=target))
            ]]), request_timeout=10)
    except (TelegramAPIError, asyncio.TimeoutError, OSError) as exc:
        logging.getLogger(__name__).warning('Direct notification failed: %s', type(exc).__name__)
