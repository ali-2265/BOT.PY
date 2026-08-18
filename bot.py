# bot.py
import os
import logging
import sqlite3
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

# -------------------- Logging Setup --------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------- Configuration --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Web App URL - باید بعد از Deploy در Render تنظیم شود
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com/webapp/")

CHANNEL_USERNAME = "@BI_GH_AM"
CHANNEL_ID = CHANNEL_USERNAME

# -------------------- Database Setup --------------------
DB_PATH = "bot_data.db"

def init_db():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table to store user authorization status
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_authorized BOOLEAN DEFAULT 0,
            first_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for storing text content with unique ID
    c.execute('''
        CREATE TABLE IF NOT EXISTS text_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id TEXT NOT NULL UNIQUE,
            original_text TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            channel_message_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def get_user(user_id: int) -> Optional[Dict]:
    """Get user record from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, is_authorized FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"user_id": row[0], "is_authorized": bool(row[1])}
        return None
    except Exception as e:
        logger.exception(f"Error getting user: {e}")
        return None

def create_or_update_user(user_id: int, is_authorized: bool = False) -> None:
    """Create or update user in database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (user_id, is_authorized) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET is_authorized = excluded.is_authorized",
            (user_id, is_authorized)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception(f"Error creating/updating user: {e}")

def save_text_content(unique_id: str, original_text: str, user_id: int, channel_message_id: int) -> bool:
    """Save text content with unique ID in database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO text_contents (unique_id, original_text, user_id, channel_message_id) "
            "VALUES (?, ?, ?, ?)",
            (unique_id, original_text, user_id, channel_message_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Text saved with unique_id: {unique_id}")
        return True
    except Exception as e:
        logger.exception(f"Error saving text content: {e}")
        return False

def get_text_content(unique_id: str) -> Optional[str]:
    """Retrieve original text by unique ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT original_text FROM text_contents WHERE unique_id = ?", (unique_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            logger.info(f"Text found in database for ID: {unique_id}")
            return row[0]
        else:
            logger.warning(f"No text found in database for ID: {unique_id}")
            return None
    except Exception as e:
        logger.exception(f"Database error in get_text_content: {e}")
        return None

def update_channel_message_id(unique_id: str, channel_message_id: int) -> bool:
    """Update channel_message_id for a given unique_id."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE text_contents SET channel_message_id = ? WHERE unique_id = ?",
            (channel_message_id, unique_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated channel_message_id for unique_id: {unique_id}")
        return True
    except Exception as e:
        logger.exception(f"Error updating channel_message_id: {e}")
        return False

# -------------------- Helper Functions --------------------
async def check_bot_admin_status(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the bot is an administrator in the channel."""
    try:
        bot_member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=context.bot.id
        )
        is_admin = bot_member.status in ['administrator', 'creator']
        logger.info(f"Bot admin status: {is_admin}")
        return is_admin
    except TelegramError as e:
        logger.error(f"Error checking bot admin status: {e}")
        return False

async def is_user_authorized(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is authorized to post messages."""
    if not await check_bot_admin_status(context):
        return False
    
    user = get_user(user_id)
    is_auth = user and user["is_authorized"]
    logger.info(f"User {user_id} authorized: {is_auth}")
    return is_auth

async def send_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> Tuple[int, str]:
    """Send a message to the channel with inline button."""
    # Channel fixed message with fancy formatting
    channel_message = (
        "┏━━━━━◥◣◆◢◤━━━━━┓\n"
        "   ᯽ VIP -- ALI ᯽\n"
        "   ᯽ VIP -- BI GHAM ᯽\n"
        "   ᯽ @BI_GH_AM ᯽\n"
        "┗━━━━━◥◣◆◢◤━━━━━┛"
    )
    
    # Generate unique ID for this text
    unique_id = str(uuid.uuid4())
    logger.info(f"Generated unique_id: {unique_id}")
    
    # Save text to database before creating button
    save_success = save_text_content(
        unique_id=unique_id,
        original_text=text,
        user_id=update.effective_user.id,
        channel_message_id=0
    )
    
    if not save_success:
        logger.error(f"Failed to save text content for unique_id: {unique_id}")
        raise Exception("Failed to save text content")
    
    # Create inline keyboard with Web App button
    webapp_url = f"{WEBAPP_URL}?text_id={unique_id}"
    keyboard = [[
        InlineKeyboardButton(
            "𝐁𝐈 𝐆𝐇𝐀𝐌",
            web_app=WebAppInfo(url=webapp_url)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send message to channel
    try:
        channel_msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_message,
            reply_markup=reply_markup
        )
        logger.info(f"Channel message sent: {channel_msg.message_id}")
        
        update_channel_message_id(unique_id, channel_msg.message_id)
        
        return channel_msg.message_id, unique_id
    except TelegramError as e:
        logger.error(f"Error sending message to channel: {e}")
        raise

# -------------------- Handlers --------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"Start command from user: {user_id}")
    
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        create_or_update_user(user_id, True)
        
        welcome_text = (
            f"👋 سلام {user.first_name}!\n\n"
            "ربات آماده است.\n"
            "برای ارسال متن به کانال، روی دکمه زیر بزنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
    else:
        create_or_update_user(user_id, False)
        
        welcome_text = (
            f"👋 سلام {user.first_name}!\n\n"
            "❌ برای استفاده از ربات، ابتدا باید ربات را در کانال @BI_GH_AM به عنوان Administrator اضافه کنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("✅ ربات را ادمین کردم", callback_data="check_admin")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    user_id = update.effective_user.id
    logger.info(f"Cancel command from user: {user_id}")
    
    context.user_data.clear()
    
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        welcome_text = (
            f"👋 سلام {update.effective_user.first_name}!\n\n"
            "ربات آماده است.\n"
            "برای ارسال متن به کانال، روی دکمه زیر بزنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ ارسال متن لغو شد.\n\n" + welcome_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ عملیات لغو شد.\n"
            "برای شروع مجدد از /start استفاده کنید."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries."""
    query = update.callback_query
    logger.info(f"Callback received: {query.data} from user: {query.from_user.id}")
    
    if query.data == "check_admin":
        await handle_check_admin(update, context)
        return
    
    if query.data == "send_text":
        await handle_send_text(update, context)
        return
    
    if query.data == "retry":
        await handle_retry(update, context)
        return
    
    if query.data == "cancel_operation":
        await handle_cancel(update, context)
        return
    
    logger.warning(f"Unknown callback: {query.data}")
    await query.answer("❌ دستور نامعتبر.", show_alert=True)

async def handle_check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle checking if bot is admin in channel."""
    query = update.callback_query
    user_id = update.effective_user.id
    logger.info(f"Check admin from user: {user_id}")
    
    await query.answer()
    
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        create_or_update_user(user_id, True)
        
        welcome_text = (
            "✅ تأیید شد.\n\n"
            "ربات آماده استفاده است.\n"
            "برای ارسال متن به کانال، روی دکمه زیر بزنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup
        )
    else:
        keyboard = [[
            InlineKeyboardButton("🔄 بررسی مجدد", callback_data="retry")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ ربات هنوز Administrator نشده است.\n"
            "لطفاً ابتدا آن را در کانال ادمین کنید و دوباره تلاش کنید.",
            reply_markup=reply_markup
        )

async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle retry button click."""
    query = update.callback_query
    user_id = update.effective_user.id
    logger.info(f"Retry from user: {user_id}")
    
    await query.answer()
    
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        create_or_update_user(user_id, True)
        
        welcome_text = (
            "✅ تأیید شد.\n\n"
            "ربات آماده استفاده است.\n"
            "برای ارسال متن به کانال، روی دکمه زیر بزنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ ربات همچنان Administrator نیست.\n"
            "لطفاً ابتدا ربات را در کانال ادمین کنید."
        )

async def handle_send_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle send text button click."""
    query = update.callback_query
    user_id = update.effective_user.id
    logger.info(f"Send text from user: {user_id}")
    
    await query.answer()
    
    is_admin = await check_bot_admin_status(context)
    
    if not is_admin:
        welcome_text = (
            "❌ ربات دیگر Administrator نیست.\n"
            "لطفاً مجدداً ربات را در کانال ادمین کنید."
        )
        
        keyboard = [[
            InlineKeyboardButton("✅ ربات را ادمین کردم", callback_data="check_admin")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup
        )
        return
    
    context.user_data['waiting_for_text'] = True
    
    await query.edit_message_text(
        "📝 لطفاً متن موردنظر خود را ارسال کنید."
    )

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel button from inline keyboard."""
    query = update.callback_query
    logger.info(f"Cancel from user: {query.from_user.id}")
    await query.answer()
    await query.edit_message_text(
        "❌ عملیات لغو شد.\n"
        "برای شروع مجدد از /start استفاده کنید."
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from users."""
    user_id = update.effective_user.id
    text = update.message.text
    logger.info(f"Text message from user: {user_id}")
    
    if context.user_data.get('waiting_for_text'):
        logger.info(f"User {user_id} is in text receiving mode")
        
        if not await check_bot_admin_status(context):
            context.user_data['waiting_for_text'] = False
            keyboard = [[
                InlineKeyboardButton("✅ ربات را ادمین کردم", callback_data="check_admin")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ ربات دیگر Administrator نیست.\n"
                "لطفاً مجدداً ربات را در کانال ادمین کنید.",
                reply_markup=reply_markup
            )
            return
        
        try:
            channel_msg_id, unique_id = await send_channel_message(update, context, text)
            logger.info(f"Message sent to channel: {channel_msg_id}, unique_id: {unique_id}")
            
            context.user_data['waiting_for_text'] = False
            
            success_text = (
                "✅ متن شما با موفقیت در کانال منتشر شد.\n\n"
                "برای ارسال متن جدید، روی دکمه زیر بزنید."
            )
            
            keyboard = [[
                InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                success_text,
                reply_markup=reply_markup
            )
            
        except TelegramError as e:
            logger.error(f"Error sending message: {e}")
            context.user_data['waiting_for_text'] = False
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام به کانال: {str(e)}"
            )
        
        return
    
    if not await is_user_authorized(user_id, context):
        if not await check_bot_admin_status(context):
            keyboard = [[
                InlineKeyboardButton("✅ ربات را ادمین کردم", callback_data="check_admin")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ ربات در کانال ادمین نیست.\n"
                "لطفاً ابتدا ربات را در کانال ادمین کنید.",
                reply_markup=reply_markup
            )
        else:
            create_or_update_user(user_id, True)
            welcome_text = (
                f"👋 سلام {update.effective_user.first_name}!\n\n"
                "ربات آماده است.\n"
                "برای ارسال متن به کانال، روی دکمه زیر بزنید."
            )
            keyboard = [[
                InlineKeyboardButton("📤 ارسال متن", callback_data="send_text")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
        return

async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle non-text messages."""
    logger.info(f"Non-text message from user: {update.effective_user.id}")
    await update.message.reply_text(
        "❌ لطفاً فقط متن ارسال کنید.\n"
        "ربات فعلاً فقط از ارسال متن پشتیبانی می‌کند."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )
    except Exception:
        pass

# -------------------- Main Application --------------------
def main() -> None:
    """Start the bot."""
    try:
        init_db()
        
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("Application created successfully.")
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        logger.info("Command handlers added.")
        
        application.add_handler(CallbackQueryHandler(button_callback))
        logger.info("Callback handler added.")
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_unknown_message))
        logger.info("Message handlers added.")
        
        application.add_error_handler(error_handler)
        logger.info("Error handler added.")
        
        logger.info("Starting bot...")
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            logger.info("Event loop found.")
        except RuntimeError:
            logger.info("No event loop found, creating a new one...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    main()
