import asyncio
from datetime import UTC, date, datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import WebAppInfo
from sqlalchemy import func, select
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Report, User
from app.services.matching import active_match, end_match, find_or_queue, leave_queue
from app.services.users import age_on, apply_referral_reward, consume_share, days_left, get_or_create, referral_count
from app.services.visuals import vs_card
from app.i18n import tr

router = Router(); cfg = settings()

class Register(StatesGroup):
    terms = State(); birthday = State(); city = State(); photo = State()
class Filter(StatesGroup):
    city = State(); ages = State()

def main_menu(lang="uz"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang,"random"), callback_data="match_menu")],
        [InlineKeyboardButton(text=tr(lang,"profile"), callback_data="profile"), InlineKeyboardButton(text=tr(lang,"leaders"), callback_data="leaders")],
        [InlineKeyboardButton(text=tr(lang,"invite"), callback_data="invite"), InlineKeyboardButton(text=tr(lang,"rules"), callback_data="rules")],
        [InlineKeyboardButton(text=tr(lang,"language"), callback_data="language")],
    ])

def match_menu(lang="uz"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang,"anonymous"), callback_data="mode:anonymous"), InlineKeyboardButton(text=tr(lang,"open"), callback_data="mode:open")],
        [InlineKeyboardButton(text=tr(lang,"back"), callback_data="home")],
    ])

def controls(lang="uz"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,"next"), callback_data="next"), InlineKeyboardButton(text=tr(lang,"stop"), callback_data="stop")], [InlineKeyboardButton(text=tr(lang,"report"), callback_data="report")]])

def language_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:uz"), InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]])

TERMS = """🛡 <b>Xavfsiz chat qoidalari</b>\n\nSuhbatda haqorat, kamsitish, firibgarlik, tahdid, shaxsiy ma’lumot tarqatish, jinsiy ekspluatatsiya va noqonuniy kontent qat’iyan man etiladi. Qoidabuzarlik botdan bloklashga, dalillar saqlanishiga va zarur holatda vakolatli organlarga murojaat qilinishiga olib kelishi mumkin.\n\nDavom etish bilan qoidalar va maxfiylik tartibiga rozilik bildirasiz. Bu bildirishnoma davlat organlarining alohida protsessual qarorlarini almashtirmaydi."""

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    args = (message.text or "").split(maxsplit=1); ref = None
    if len(args) == 2 and args[1].startswith("ref_"):
        try: ref = int(args[1][4:])
        except ValueError: pass
    async with SessionLocal() as session:
        user = await get_or_create(session, message.from_user.id, message.from_user.username, message.from_user.full_name, ref)
        registered = user.is_registered; await session.commit()
    if cfg.webapp_url:
        await state.clear()
        await message.answer("⚔️ PVP Chat — Mini App’ni oching", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ Mini App’ni ochish", web_app=WebAppInfo(url=cfg.webapp_url))]]))
        return
    if registered: await message.answer(tr(user.language,"welcome"), reply_markup=main_menu(user.language)); return
    await state.set_state(Register.terms)
    await message.answer(tr("uz","choose"), reply_markup=language_menu())

@router.callback_query(F.data == "language")
async def language(q: CallbackQuery):
    await q.message.edit_text(tr("uz","choose"), reply_markup=language_menu())

@router.callback_query(F.data.startswith("lang:"))
async def set_language(q: CallbackQuery, state: FSMContext):
    lang = q.data.split(":", 1)[1]
    async with SessionLocal() as s:
        u = await s.get(User, q.from_user.id); u.language = lang; await s.commit()
    if await state.get_state() == Register.terms.state:
        await q.message.edit_text(tr(lang,"terms"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,"agree"), callback_data="terms_yes"), InlineKeyboardButton(text=tr(lang,"decline"), callback_data="terms_no")]]))
    else: await q.message.edit_text(tr(lang,"changed"), reply_markup=main_menu(lang))

@router.callback_query(F.data == "terms_yes", Register.terms)
async def terms_yes(q: CallbackQuery, state: FSMContext):
    async with SessionLocal() as s: lang = (await s.get(User,q.from_user.id)).language
    await state.set_state(Register.birthday); await q.message.edit_text(tr(lang,"birthday"))

@router.callback_query(F.data == "terms_no", Register.terms)
async def terms_no(q: CallbackQuery): await q.message.edit_text("Ro‘yxatdan o‘tish uchun qoidalarga rozilik kerak.")

@router.message(Register.birthday)
async def birthday(message: Message, state: FSMContext):
    try: born = date.fromisoformat(message.text.strip())
    except (ValueError, AttributeError): await message.answer("Format: 2000-12-31"); return
    if age_on(born) < cfg.min_age or born > date.today(): await message.answer("Bu chat faqat 18+ uchun. To‘g‘ri sanani kiriting."); return
    await state.update_data(birth_date=born.isoformat()); await state.set_state(Register.city)
    async with SessionLocal() as s: lang = (await s.get(User,message.from_user.id)).language
    await message.answer(tr(lang,"city"))

@router.message(Register.city)
async def city(message: Message, state: FSMContext):
    city = (message.text or "").strip()
    if not 2 <= len(city) <= 100: await message.answer("Shahar nomini kiriting."); return
    await state.update_data(city=city); await state.set_state(Register.photo)
    async with SessionLocal() as s: lang = (await s.get(User,message.from_user.id)).language
    await message.answer(tr(lang,"photo"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,"default"), callback_data="default_avatar")]]))

async def finish_registration(message: Message, state: FSMContext, photo_id: str | None, user_id: int | None = None):
    data = await state.get_data()
    user_id = user_id or message.from_user.id
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        user.birth_date, user.city = date.fromisoformat(data["birth_date"]), data["city"]
        user.avatar_file_id, user.avatar_is_default = photo_id, photo_id is None
        user.terms_accepted_at, user.terms_version, user.is_registered = datetime.now(UTC), cfg.terms_version, True
        await apply_referral_reward(session, user); await session.commit()
    await state.clear(); await message.answer(tr(user.language,"registered"), reply_markup=main_menu(user.language))

@router.message(Register.photo, F.photo)
async def save_photo(message: Message, state: FSMContext): await finish_registration(message, state, message.photo[-1].file_id)
@router.callback_query(F.data == "default_avatar", Register.photo)
async def default_avatar(q: CallbackQuery, state: FSMContext): await finish_registration(q.message, state, None, q.from_user.id)

@router.callback_query(F.data == "home")
async def home(q: CallbackQuery):
    async with SessionLocal() as s: lang = (await s.get(User,q.from_user.id)).language
    await q.message.edit_text("Main menu" if lang == "en" else "Главное меню" if lang == "ru" else "Bosh menyu", reply_markup=main_menu(lang))

@router.callback_query(F.data == "rules")
async def rules(q: CallbackQuery):
    async with SessionLocal() as s: lang = (await s.get(User,q.from_user.id)).language
    await q.message.edit_text(tr(lang,"terms"), parse_mode="HTML", reply_markup=main_menu(lang))

@router.callback_query(F.data == "profile")
async def profile(q: CallbackQuery):
    async with SessionLocal() as s:
        u = await s.get(User, q.from_user.id); refs = await referral_count(s, u.telegram_id)
    badges = ("✅ Tasdiqlangan\n" if u.is_verified else "") + ("🥇 Gold\n" if days_left(u.gold_until) else "")
    text = f"👤 <b>{u.display_name}</b>\n🏙 {u.city}\n🎂 {age_on(u.birth_date)} yosh\n{badges}💎 Premium: {days_left(u.premium_until)} kun\n🥇 Gold: {days_left(u.gold_until)} kun\n🎁 Referral: {refs}"
    await q.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(u.language))

@router.callback_query(F.data == "invite")
async def invite(q: CallbackQuery):
    async with SessionLocal() as s:
        if not await consume_share(s, q.from_user.id): await q.answer("Bugungi 15 ta ulashish limiti tugadi.", show_alert=True); return
        refs = await referral_count(s, q.from_user.id); await s.commit()
    link = f"https://t.me/{cfg.public_bot_username}?start=ref_{q.from_user.id}"
    await q.message.edit_text(f"🎁 Sizning havolangiz:\n<code>{link}</code>\n\nTasdiqlangan referral: {refs}. 5 ta = 30 kun Premium, 50 ta = 30 kun Gold. Kuniga havolani 15 marta ulashish mumkin.", parse_mode="HTML", reply_markup=main_menu())

@router.callback_query(F.data == "leaders")
async def leaders(q: CallbackQuery):
    async with SessionLocal() as s:
        referred = User.__table__.alias("referred")
        referrer = User.__table__.alias("referrer")
        rows = (await s.execute(select(referrer.c.display_name, func.count(referred.c.telegram_id).label("n")).join(referrer, referred.c.referred_by_id == referrer.c.telegram_id).where(referred.c.referral_rewarded.is_(True)).group_by(referrer.c.telegram_id, referrer.c.display_name).order_by(func.count(referred.c.telegram_id).desc()).limit(10))).all()
    lines = [f"{i}. {name} — {count}" for i, (name, count) in enumerate(rows, 1)] or ["Hali natijalar yo‘q."]
    await q.message.edit_text("🏆 <b>Top 10 referralchilar</b>\n\n" + "\n".join(lines) + "\n\nTop-10’ga oyiga 30 kun Gold beriladi (admin tomonidan yakunlanadi).", parse_mode="HTML", reply_markup=main_menu())

@router.callback_query(F.data == "match_menu")
async def choose_mode(q: CallbackQuery):
    async with SessionLocal() as s: lang = (await s.get(User,q.from_user.id)).language
    await q.message.edit_text("Chat mode:" if lang == "en" else "Режим чата:" if lang == "ru" else "Chat turini tanlang:", reply_markup=match_menu(lang))

@router.callback_query(F.data.startswith("mode:"))
async def choose_filter(q: CallbackQuery, state: FSMContext):
    await state.update_data(mode=q.data.split(":", 1)[1]); await state.set_state(Filter.city)
    await q.message.edit_text("Filtr shahri: nomini yuboring, yoki <b>-</b> yuboring — istalgan shahar.", parse_mode="HTML")

@router.message(Filter.city)
async def filter_city(message: Message, state: FSMContext):
    city = (message.text or "").strip(); city = None if city == "-" else city
    if city and not 2 <= len(city) <= 100: await message.answer("Shahar nomini yoki - yuboring."); return
    await state.update_data(city_filter=city); await state.set_state(Filter.ages)
    await message.answer("Yosh oralig‘i: masalan <b>18-30</b>, yoki <b>-</b> (istalgan yosh).", parse_mode="HTML")

@router.message(Filter.ages)
async def queue_for_match(message: Message, state: FSMContext):
    raw = (message.text or "").strip(); minimum = maximum = None
    if raw != "-":
        try:
            minimum, maximum = map(int, raw.split("-"))
            if minimum < cfg.min_age or maximum < minimum or maximum > 100: raise ValueError
        except ValueError: await message.answer("Format: 18-30 yoki -"); return
    data = await state.get_data(); await state.clear()
    async with SessionLocal() as s:
        user = await s.get(User, message.from_user.id)
        match, partner = await find_or_queue(s, user, data["mode"], data["city_filter"], minimum, maximum); await s.commit()
    if not match:
        await message.answer("🔎 Mos raqib qidirilmoqda… Sizni kutish navbatiga qo‘shdik.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Bekor qilish", callback_data="stop")]])); return
    await announce_match(message.bot, match, user, partner)

async def announce_match(bot: Bot, match, one: User, two: User):
    # The generated card is deliberately anonymous when that mode was selected.
    if match.mode == "anonymous":
        one_card, two_card = "🕶 Noma’lum", "🕶 Noma’lum"
    else:
        one_card, two_card = f"{one.display_name}, {age_on(one.birth_date)}\n{one.city}", f"{two.display_name}, {age_on(two.birth_date)}\n{two.city}"
    caption = "⚔️ <b>MATCH TOPILDI</b>\n\n3… 2… 1… <b>SUHBAT BOSHLANDI!</b>"
    await bot.send_photo(one.telegram_id, vs_card(one_card, two_card), caption=caption, parse_mode="HTML", reply_markup=controls(one.language))
    await bot.send_photo(two.telegram_id, vs_card(two_card, one_card), caption=caption, parse_mode="HTML", reply_markup=controls(two.language))

@router.callback_query(F.data == "stop")
async def stop(q: CallbackQuery):
    async with SessionLocal() as s:
        await leave_queue(s, q.from_user.id); match = await active_match(s, q.from_user.id)
        partner_id = None
        if match:
            partner_id = match.user_two_id if match.user_one_id == q.from_user.id else match.user_one_id
            await end_match(s, match)
        await s.commit()
    await q.message.answer("🚫 Chat to‘xtatildi.", reply_markup=main_menu())
    if partner_id: await q.bot.send_message(partner_id, "Suhbatdosh chatni yakunladi.", reply_markup=main_menu())

@router.callback_query(F.data == "next")
async def next_match(q: CallbackQuery):
    await stop(q); await q.message.answer("Yangi raqib uchun ⚔️ Random chat tugmasini bosing.", reply_markup=main_menu())

@router.callback_query(F.data == "report")
async def report(q: CallbackQuery):
    async with SessionLocal() as s:
        match = await active_match(s, q.from_user.id)
        if not match: await q.answer("Faol chat yo‘q.", show_alert=True); return
        target = match.user_two_id if match.user_one_id == q.from_user.id else match.user_one_id
        s.add(Report(reporter_id=q.from_user.id, reported_id=target, match_id=match.id, reason="User report")); await s.commit()
    await q.answer("Shikoyat qabul qilindi. Admin tekshiradi.", show_alert=True)

@router.message(F.text | F.photo | F.video | F.voice | F.document | F.sticker)
async def relay(message: Message):
    if not message.from_user: return
    async with SessionLocal() as s:
        user = await s.get(User, message.from_user.id)
        match = await active_match(s, message.from_user.id)
        if not user or user.is_banned or not match: return
        target = match.user_two_id if match.user_one_id == user.telegram_id else match.user_one_id
    try: await message.copy_to(target)
    except Exception: await message.answer("Xabar yuborilmadi. Suhbat yakunlangan bo‘lishi mumkin.")

async def main():
    await init_db(); bot = Bot(cfg.bot_token); dp = Dispatcher(); dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
