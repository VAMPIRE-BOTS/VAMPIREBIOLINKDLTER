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
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8602860906:AAFyhn5AH9ALnRt7DsDSoV496Z2K3Y-B_Bc")
MONGO_URI = os.getenv("mongodb+srv://TEAM-VAMPIRE-OP:VAMPIRE800@team-vampire-op.npkrxta.mongodb.net/?appName=TEAM-VAMPIRE-OP")
OWNER_ID = int(os.getenv("8628886006", "0"))
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/VAMPIREUPDATES")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "https://t.me/lVAMPIRE_KINGl")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.bio_link_bot
approved_users = db.approved_users

BIO_LINK_PATTERN = re.compile(
    r'(https?://|t\.me/|telegram\.me/|@\w+)',
    re.IGNORECASE
)


async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


async def is_approved(user_id: int) -> bool:
    user = await approved_users.find_one({"user_id": user_id})
    return bool(user)


@dp.message(Command("start"))
async def start_command(message: Message):
    buttons = InlineKeyboardBuilder()
    buttons.button(text="👑 Owner", url=OWNER_USERNAME)
    buttons.button(text="🆘 Support", url=SUPPORT_CHANNEL)
    buttons.button(text="📚 Help", callback_data="help_menu")
    buttons.adjust(2, 1)

    text = (
        "<b>👋 Hello! I am Bio Link Deleter Bot</b>\n\n"
        "I automatically detect and remove messages from users who have promotional links in their Telegram bio.\n\n"
        "✅ Removes spam automatically\n"
        "✅ Keeps your group clean and safe\n"
        "✅ Ignores admins and approved users\n"
        "✅ Easy to use and fully secure\n\n"
        "Add me to your group and promote me as an admin to start protection."
    )

    await message.answer(text, reply_markup=buttons.as_markup())


@dp.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery):
    text = (
        "<b>📚 Available Commands</b>\n\n"
        "/start - Start the bot\n"
        "/help - Show help menu\n"
        "/approve - Approve a replied user\n"
        "/unapprove - Remove approval from a user\n"
        "/approved - View approved users count\n\n"
        "<b>How it works:</b>\n"
        "• Detects users with links in their bio\n"
        "• Deletes their messages automatically\n"
        "• Sends a warning message\n"
        "• Admins and approved users are ignored"
    )
    await callback.message.answer(text)
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: Message):
    await help_menu(type("obj", (), {"message": message, "answer": lambda *args, **kwargs: None})())


@dp.message(Command("approve"))
async def approve_user(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins can use this command.")

    if not message.reply_to_message:
        return await message.reply("Reply to a user's message to approve them.")

    user = message.reply_to_message.from_user
    await approved_users.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id, "name": user.full_name}},
        upsert=True
    )
    await message.reply(f"✅ {user.full_name} has been approved.")


@dp.message(Command("unapprove"))
async def unapprove_user(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("❌ Only admins can use this command.")

    if not message.reply_to_message:
        return await message.reply("Reply to a user's message to unapprove them.")

    user = message.reply_to_message.from_user
    await approved_users.delete_one({"user_id": user.id})
    await message.reply(f"✅ {user.full_name} has been unapproved.")


@dp.message(Command("approved"))
async def approved_count(message: Message):
    count = await approved_users.count_documents({})
    await message.reply(f"✅ Total approved users: {count}")


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
    except Exception:
        bio = ""

    if BIO_LINK_PATTERN.search(bio):
        try:
            await message.delete()
            warning = await message.answer(
                f"⚠️ {user.mention_html()}, please remove your bio link and send your message again."
            )
            await asyncio.sleep(10)
            await warning.delete()
        except Exception as e:
            logging.error(f"Failed to delete message: {e}")


async def main():
    logging.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
