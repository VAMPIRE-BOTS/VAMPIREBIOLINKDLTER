import os
import re
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from motor.motor_asyncio import AsyncIOMotorClient

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

IMAGE_URL = "https://i.ibb.co/Zj7Xckf/x.jpg"

OWNER_LINK = "https://t.me/lVAMPIRE_KINGl"
SUPPORT_LINK = "https://t.me/VAMPIREUPDATES"

# ====== CHECK ======
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")
if not MONGO_URI:
    raise ValueError("MONGO_URI missing")

# ====== SETUP ======
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.bio_link_bot
approved_users = db.approved_users
warnings_db = db.warnings

BIO_LINK_PATTERN = re.compile(r'(https?://|t\.me/|@\w+)', re.I)

# ====== FUNCTIONS ======
async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

async def get_warning(user_id):
    data = await warnings_db.find_one({"user_id": user_id})
    return data["count"] if data else 0

async def add_warning(user_id):
    await warnings_db.update_one(
        {"user_id": user_id},
        {"$inc": {"count": 1}},
        upsert=True
    )

# ====== START ======
@dp.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="👑 Owner", url=OWNER_LINK)
    kb.button(text="🆘 Support", url=SUPPORT_LINK)
    kb.button(text="📚 Help", callback_data="help")
    kb.adjust(2, 1)

    text = (
        "<b>👋 Hey! I am Bio Link Deleter Bot</b>\n\n"
        "I help keep your group clean and safe.\n\n"
        "🚫 I automatically detect users who have promotional links in their bio\n"
        "🧹 I delete their messages instantly\n"
        "⚠️ I give warnings before taking strict action\n\n"
        "💡 Just add me to your group and make me admin.\n"
        "Enjoy a spam-free experience 😎"
    )

    await message.answer_photo(IMAGE_URL, caption=text, reply_markup=kb.as_markup())

# ====== HELP ======
@dp.callback_query(F.data == "help")
async def help_cb(callback: CallbackQuery):
    text = (
        "<b>📚 Commands & Usage</b>\n\n"
        "/start - Start the bot\n"
        "👉 Shows welcome message\n\n"
        "/approve - Approve user\n"
        "👉 Allows user to bypass protection\n\n"
        "/unapprove - Remove approval\n"
        "👉 User will be checked again\n\n"
        "/approved - Show approved users count\n"
        "👉 Displays total approved users\n\n"
        "<b>System:</b>\n"
        "• Detects bio links\n"
        "• Gives 3 warnings\n"
        "• After 3 warnings → Auto mute (if possible)"
    )

    await callback.message.answer(text)
    await callback.answer()

# ====== APPROVE ======
@dp.message(Command("approve"))
async def approve(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins")

    user = None

    if message.reply_to_message:
        user = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) > 1:
            try:
                user_id = int(args[1])
                user = await bot.get_chat(user_id)
            except:
                pass

    if not user:
        return await message.reply("Reply or give user_id")

    await approved_users.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id}},
        upsert=True
    )

    await message.reply(f"✅ Approved: {user.mention_html()}")

# ====== UNAPPROVE ======
@dp.message(Command("unapprove"))
async def unapprove(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins")

    if not message.reply_to_message:
        return await message.reply("Reply user")

    user = message.reply_to_message.from_user
    await approved_users.delete_one({"user_id": user.id})

    await message.reply("✅ Unapproved")

# ====== FILTER ======
@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def filter_msg(message: Message):
    user = message.from_user

    if await is_admin(message.chat.id, user.id):
        return

    if await approved_users.find_one({"user_id": user.id}):
        return

    try:
        data = await bot.get_chat(user.id)
        bio = data.bio or ""
    except:
        bio = ""

    if BIO_LINK_PATTERN.search(bio):
        await message.delete()

        count = await get_warning(user.id)
        await add_warning(user.id)
        count += 1

        warn_msg = await message.answer(
            f"⚠️ {user.mention_html()}\n"
            f"Please remove your bio link and send again.\n"
            f"Warning: {count}/3"
        )

        await asyncio.sleep(8)
        await warn_msg.delete()

        if count >= 3:
            try:
                await bot.restrict_chat_member(
                    message.chat.id,
                    user.id,
                    permissions={}
                )
                await message.answer(f"🔇 {user.mention_html()} muted (3 warnings)")
            except:
                pass

# ====== MAIN ======
async def main():
    print("Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
