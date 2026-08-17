# bot.py
import os
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatType
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

CHANNEL_USERNAME = "@BI_GH_AM"
CHANNEL_ID = CHANNEL_USERNAME  # Works with username format for API calls

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
    
    # Table to store messages for callback data
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            original_text TEXT,
            channel_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Optional[Dict]:
    """Get user record from database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, is_authorized FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "is_authorized": bool(row[1])}
    return None

def create_or_update_user(user_id: int, is_authorized: bool = False) -> None:
    """Create or update user in database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, is_authorized) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET is_authorized = excluded.is_authorized",
        (user_id, is_authorized)
    )
    conn.commit()
    conn.close()

def save_message(message_id: int, user_id: int, original_text: str, channel_message_id: int) -> int:
    """Save message mapping and return its database ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (message_id, user_id, original_text, channel_message_id) "
        "VALUES (?, ?, ?, ?)",
        (message_id, user_id, original_text, channel_message_id)
    )
    db_id = c.lastrowid
    conn.commit()
    conn.close()
    return db_id

def get_original_text(db_id: int) -> Optional[str]:
    """Retrieve original text by database ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_text FROM messages WHERE id = ?", (db_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# -------------------- Helper Functions --------------------
async def check_bot_admin_status(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the bot is an administrator in the channel."""
    try:
        bot_member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=context.bot.id
        )
        return bot_member.status in ['administrator', 'creator']
    except TelegramError as e:
        logger.error(f"Error checking bot admin status: {e}")
        return False

async def is_user_authorized(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is authorized to post messages."""
    # First check if bot is admin in channel
    if not await check_bot_admin_status(context):
        return False
    
    # Then check user's authorization status
    user = get_user(user_id)
    return user and user["is_authorized"]

async def send_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Send a message to the channel with inline button."""
    # Channel header
    channel_header = (
        "VIP ALI\n"
        "VIP BI GHAM\n"
        "@BI_GH_AM\n\n"
    )
    
    full_text = channel_header + text
    
    # Create inline keyboard with callback data
    keyboard = [[
        InlineKeyboardButton(
            "👁 نمایش متن",
            callback_data=f"show_{update.effective_user.id}_{datetime.now().timestamp()}"
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send message to channel
    try:
        channel_msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=full_text,
            reply_markup=reply_markup
        )
        return channel_msg.message_id
    except TelegramError as e:
        logger.error(f"Error sending message to channel: {e}")
        raise

# -------------------- Handlers --------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    
    # Create or get user
    create_or_update_user(user_id, False)
    
    welcome_text = (
        f"👋 سلام {user.first_name}!\n\n"
        "به ربات پست‌گذار کانال خوش آمدید.\n"
        "برای استفاده از این ربات، ابتدا باید ربات را در کانال ادمین کنید.\n\n"
        "کانال: @BI_GH_AM"
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
    await update.message.reply_text(
        "❌ عملیات لغو شد.\n"
        "برای شروع مجدد از /start استفاده کنید."
    )
    # Clear any user data if needed
    context.user_data.clear()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries."""
    query = update.callback_query
    await query.answer()  # Always answer callback to avoid timeout
    
    user_id = update.effective_user.id
    
    # Handle "check_admin" callback
    if query.data == "check_admin":
        await handle_check_admin(update, context)
        return
    
    # Handle "show_text" callback
    if query.data.startswith("show_"):
        await handle_show_text(update, context)
        return
    
    # Handle "retry" callback
    if query.data == "retry":
        await handle_retry(update, context)
        return
    
    # Handle "cancel" callback
    if query.data == "cancel_operation":
        await handle_cancel(update, context)
        return
    
    # Unknown callback
    await query.edit_message_text("❌ دستور نامعتبر.")

async def handle_check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle checking if bot is admin in channel."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Check if bot is admin
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        # Update user as authorized
        create_or_update_user(user_id, True)
        
        await query.edit_message_text(
            "✅ ربات با موفقیت ادمین شد.\n"
            "حالا متن موردنظر خود را ارسال کنید."
        )
    else:
        # Create retry button
        keyboard = [[
            InlineKeyboardButton("🔄 بررسی مجدد", callback_data="retry")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ هنوز ربات را ادمین نکرده‌اید.\n"
            "ابتدا ربات را در کانال ادمین کنید و دوباره روی دکمه بزنید.",
            reply_markup=reply_markup
        )

async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle retry button click."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Check if bot is admin
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        # Update user as authorized
        create_or_update_user(user_id, True)
        
        await query.edit_message_text(
            "✅ ربات با موفقیت ادمین شد.\n"
            "حالا متن موردنظر خود را ارسال کنید."
        )
    else:
        await query.edit_message_text(
            "❌ همچنان ربات ادمین نیست.\n"
            "لطفاً ابتدا ربات را در کانال ادمین کنید."
        )

async def handle_show_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle showing original text when button is clicked."""
    query = update.callback_query
    callback_data = query.data
    
    try:
        # Extract database ID from callback data
        # Format: show_{user_id}_{timestamp}
        parts = callback_data.split('_')
        if len(parts) < 3:
            await query.answer("❌ داده نامعتبر.", show_alert=True)
            return
        
        # We'll use the timestamp to find the message
        # For simplicity, we'll search by user_id and latest message
        # In production, you'd want to store the mapping properly
        
        user_id = int(parts[1])
        
        # Get the original text from database
        # For this simple implementation, we'll get the latest message from this user
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT original_text FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = c.fetchone()
        conn.close()
        
        if row and row[0]:
            await query.answer(f"📝 متن اصلی:\n\n{row[0]}", show_alert=True)
        else:
            await query.answer("❌ متن یافت نشد.", show_alert=True)
            
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data: {e}")
        await query.answer("❌ خطا در نمایش متن.", show_alert=True)

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel button from inline keyboard."""
    query = update.callback_query
    await query.edit_message_text(
        "❌ عملیات لغو شد.\n"
        "برای شروع مجدد از /start استفاده کنید."
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from users."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if user is authorized
    if not await is_user_authorized(user_id, context):
        # Check if bot is admin
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
            # User not authorized
            keyboard = [[
                InlineKeyboardButton("✅ ربات را ادمین کردم", callback_data="check_admin")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ شما هنوز تأیید نشده‌اید.\n"
                "لطفاً روی دکمه زیر کلیک کنید تا دسترسی شما تأیید شود:",
                reply_markup=reply_markup
            )
        return
    
    try:
        # Send message to channel
        channel_msg_id = await send_channel_message(update, context, text)
        
        # Save message mapping
        save_message(
            message_id=update.message.message_id,
            user_id=user_id,
            original_text=text,
            channel_message_id=channel_msg_id
        )
        
        await update.message.reply_text(
            "✅ متن شما با موفقیت در کانال منتشر شد.\n"
            "برای ارسال متن جدید، کافیست متن را ارسال کنید."
        )
        
    except TelegramError as e:
        logger.error(f"Error sending message: {e}")
        await update.message.reply_text(
            f"❌ خطا در ارسال پیام به کانال: {str(e)}"
        )

async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle non-text messages (photos, videos, etc.)."""
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
    # Initialize database
    init_db()
    logger.info("Database initialized.")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_unknown_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
