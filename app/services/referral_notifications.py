"""Referral bot messages. Delivery failure must not break registration or links."""
import asyncio
import logging
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

log = logging.getLogger(__name__)
TEXT = {
    'uz': {'link':'🎁 Sizning taklif havolangiz:', 'copy':'📋 Nusxa olish', 'joined':'🎉 Siz {name}ni taklif qildingiz! U havolangiz orqali botni boshladi.\n\nRo‘yxatdan o‘tishni yakunlagach, referalingiz hisoblanadi.'},
    'ru': {'link':'🎁 Ваша ссылка для приглашения:', 'copy':'📋 Скопировать', 'joined':'🎉 Вы пригласили {name}! Пользователь запустил бота по вашей ссылке.\n\nРеферал будет засчитан после завершения регистрации.'},
    'en': {'link':'🎁 Your invite link:', 'copy':'📋 Copy link', 'joined':'🎉 You invited {name}! They started the bot using your link.\n\nThe referral will count once they complete registration.'},
}

async def deliver(bot, user_id, message, **kwargs):
    if bot is None:
        return False
    try:
        await bot.send_message(user_id, message, parse_mode=None, **kwargs)
        return True
    except (TelegramAPIError, asyncio.TimeoutError, OSError) as error:
        log.warning('Referral message delivery failed: %s', type(error).__name__)
        return False

async def send_invite_link(bot, user_id, link, language):
    words = TEXT.get(language, TEXT['uz'])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=words['copy'], copy_text=CopyTextButton(text=link))
    ]])
    return await deliver(bot, user_id, words['link']+'\n'+link, reply_markup=keyboard)

async def send_referral_started(bot, referrer_id, name, language):
    words = TEXT.get(language, TEXT['uz'])
    return await deliver(bot, referrer_id, words['joined'].format(name=name))

async def send_verification_result(bot, user_id, approved, reason=None, language='uz'):
    messages = {
        'uz': ("✅ Verifikatsiyadan muvaffaqiyatli o‘tdingiz!\n\nSilver galochka profilingiz yonida ko‘rinadi.",
               "⚠️ Verifikatsiya rad etildi.\n\nSabab: {reason}\n\nVideoni qayta yuborib, yana urinib ko‘rishingiz mumkin."),
        'ru': ("✅ Вы успешно прошли проверку!\n\nSilver-галочка появится рядом с вашим профилем.",
               "⚠️ Проверка отклонена.\n\nПричина: {reason}\n\nВы можете отправить видео повторно."),
        'en': ("✅ Verification approved!\n\nYour Silver badge now appears beside your profile.",
               "⚠️ Verification rejected.\n\nReason: {reason}\n\nYou can submit a new video and try again."),
    }
    approved_text, rejected_text = messages.get(language, messages['uz'])
    return await deliver(bot, user_id, approved_text if approved else rejected_text.format(reason=reason or 'Ko‘rsatilmagan'))
