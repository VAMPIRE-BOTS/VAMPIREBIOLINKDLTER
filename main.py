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

# ====== ENV VARIABLES ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/VAMPIREUPDATES")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "https://t.me/lVAMPIRE_KINGl")

# ====== SAFETY CHECK ======
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing! Set it in Heroku Config Vars")

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI missing! Set it in Heroku Config Vars")

# ====== LOGGING ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ====== BOT INIT ======
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ====== MONGO ======
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.bio_link_bot
approved_users = db.approved_users

BIO_LINK_PATTERN = re.compile(
    r'(https?://|t\.me/|telegram\.me/|@\w+)',
    re.IGNORECASE
)

# ====== FUNCTIONS ======
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

async def is_approved(user_id: int) -> bool:
    user = await approved_users.find_one({"user_id": user_id})
    return bool(user)

# ====== COMMANDS ======
@dp.message(Command("start"))
async def start_command(message: Message):
    buttons = InlineKeyboardBuilder()
    buttons.button(text="👑 Owner", url=OWNER_USERNAME)
    buttons.button(text="🆘 Support", url=SUPPORT_CHANNEL)
    buttons.button(text="📚 Help", callback_data="help_menu")
    buttons.adjust(2, 1)

    await message.answer(
        "<b>👋 Hello! I am Bio Link Deleter Bot</b>\n\n"
        "I automatically remove messages from users having links in bio.",
        reply_markup=buttons.as_markup()
    )

@dp.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery):
    await callback.message.answer(
        "<b>📚 Commands:</b>\n"
        "/approve - approve user\n"
        "/unapprove - remove approval\n"
        "/approved - count users"
    )
    await callback.answer()

@dp.message(Command("approve"))
async def approve_user(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins")

    if not message.reply_to_message:
        return await message.reply("Reply to user")

    user = message.reply_to_message.from_user
    await approved_users.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id}},
        upsert=True
    )
    await message.reply("✅ Approved")

@dp.message(Command("unapprove"))
async def unapprove_user(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins")

    if not message.reply_to_message:
        return await message.reply("Reply to user")

    user = message.reply_to_message.from_user
    await approved_users.delete_one({"user_id": user.id})
    await message.reply("✅ Unapproved")

@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def moderate_messages(message: Message):
    user = message.from_user

    if await is_admin(message.chat.id, user.id):
        return

    if await is_approved(user.id):
        return

    try:
        chat_member = await bot.get_chat(user.id)
        bio = chat_member.bio or ""
    except:
        bio = ""

    if BIO_LINK_PATTERN.search(bio):
        try:
            await message.delete()
        except Exception as e:
            logging.error(e)

# ====== MAIN ======
async def main():
    logging.info("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
