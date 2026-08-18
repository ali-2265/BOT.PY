# bot.py
import os
import logging
import uuid
import json
import asyncpg
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

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com/webapp/")
CHANNEL_USERNAME = "@BI_GH_AM"
CHANNEL_ID = CHANNEL_USERNAME

# -------------------- Database Connection --------------------
db_pool = None

async def init_db_pool():
    """Initialize PostgreSQL connection pool."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logger.info("Database connected successfully.")
        
        # Create tables if they don't exist
        async with db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    is_authorized BOOLEAN DEFAULT FALSE,
                    first_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS text_contents (
                    id SERIAL PRIMARY KEY,
                    unique_id TEXT UNIQUE NOT NULL,
                    original_text TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    channel_message_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.exception(f"Failed to connect to database: {e}")
        raise

async def get_db_pool():
    """Get database connection pool."""
    global db_pool
    if db_pool is None:
        await init_db_pool()
    return db_pool

# -------------------- Database Functions --------------------
async def get_user(user_id: int) -> Optional[Dict]:
    """Get user record from database."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, is_authorized FROM users WHERE user_id = $1",
                user_id
            )
            if row:
                return {"user_id": row[0], "is_authorized": row[1]}
            return None
    except Exception as e:
        logger.exception(f"Error getting user: {e}")
        return None

async def create_or_update_user(user_id: int, is_authorized: bool = False) -> None:
    """Create or update user in database."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, is_authorized) VALUES ($1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET is_authorized = EXCLUDED.is_authorized",
                user_id, is_authorized
            )
    except Exception as e:
        logger.exception(f"Error creating/updating user: {e}")

async def save_text_content(unique_id: str, original_text: str, user_id: int, channel_message_id: int) -> bool:
    """Save text content with unique ID in database."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO text_contents (unique_id, original_text, user_id, channel_message_id) "
                "VALUES ($1, $2, $3, $4)",
                unique_id, original_text, user_id, channel_message_id
            )
            logger.info(f"Text saved with unique_id: {unique_id}")
            return True
    except Exception as e:
        logger.exception(f"Error saving text content: {e}")
        return False

async def get_text_content(unique_id: str) -> Optional[str]:
    """Retrieve original text by unique ID."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT original_text FROM text_contents WHERE unique_id = $1",
                unique_id
            )
            if row:
                logger.info(f"Text found in database for ID: {unique_id}")
                return row[0]
            else:
                logger.warning(f"No text found in database for ID: {unique_id}")
                return None
    except Exception as e:
        logger.exception(f"Database error in get_text_content: {e}")
        return None

async def update_channel_message_id(unique_id: str, channel_message_id: int) -> bool:
    """Update channel_message_id for a given unique_id."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE text_contents SET channel_message_id = $1 WHERE unique_id = $2",
                channel_message_id, unique_id
            )
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
    
    user = await get_user(user_id)
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
    save_success = await save_text_content(
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
        logger.info("Sending channel message...")
        channel_msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_message,
            reply_markup=reply_markup
        )
        logger.info(f"Channel message sent successfully: {channel_msg.message_id}")
        
        await update_channel_message_id(unique_id, channel_msg.message_id)
        
        return channel_msg.message_id, unique_id
    except TelegramError as e:
        logger.exception(f"Failed to send message to channel: {e}")
        raise

# -------------------- Handlers --------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"Start command from user: {user_id}")
    
    is_admin = await check_bot_admin_status(context)
    
    if is_admin:
        await create_or_update_user(user_id, True)
        
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
        await create_or_update_user(user_id, False)
        
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
        await create_or_update_user(user_id, True)
        
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
        await create_or_update_user(user_id, True)
        
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
    logger.info(f"User {user_id} clicked send text")
    
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
    logger.info(f"User {user_id} entered text receiving mode")
    
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
    logger.info(f"Text message received from user: {user_id}")
    
    if context.user_data.get('waiting_for_text'):
        logger.info(f"User {user_id} is in text receiving mode")
        logger.info(f"Text received: {text[:50]}...")
        
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
            # Send message to channel
            logger.info("Attempting to send message to channel...")
            channel_msg_id, unique_id = await send_channel_message(update, context, text)
            logger.info(f"Message sent to channel successfully: {channel_msg_id}, unique_id: {unique_id}")
            
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
            logger.exception(f"Error sending message to channel: {e}")
            context.user_data['waiting_for_text'] = False
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام به کانال: {str(e)}"
            )
        
        return
    
    # If user is not in text receiving mode
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
            await create_or_update_user(user_id, True)
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

# -------------------- Web App Handler --------------------
async def web_app_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Web App data from users."""
    query = update.callback_query
    if not query or not query.data:
        return
    
    try:
        data = json.loads(query.data)
        if data.get('action') == 'get_text':
            text_id = data.get('text_id')
            logger.info(f"WebApp requested text for ID: {text_id}")
            
            if text_id:
                original_text = await get_text_content(text_id)
                if original_text:
                    logger.info(f"Text loaded from database for WebApp")
                    await query.answer(
                        text=original_text[:200] if len(original_text) > 200 else original_text,
                        show_alert=True
                    )
                else:
                    logger.warning(f"Text not found for WebApp ID: {text_id}")
                    await query.answer("❌ متن یافت نشد.", show_alert=True)
            else:
                await query.answer("❌ شناسه متن نامعتبر.", show_alert=True)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from WebApp: {query.data}")
    except Exception as e:
        logger.exception(f"Error in web_app_handler: {e}")
        await query.answer("❌ خطا در نمایش متن.", show_alert=True)

# -------------------- Main Application --------------------
async def main() -> None:
    """Start the bot."""
    try:
        # Initialize database
        await init_db_pool()
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("Application created successfully.")
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        logger.info("Command handlers added.")
        
        # Add callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))
        logger.info("Callback handler added.")
        
        # Add Web App handler
        application.add_handler(CallbackQueryHandler(web_app_handler, pattern="^webapp_"))
        logger.info("Web App handler added.")
        
        # Add message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_unknown_message))
        logger.info("Message handlers added.")
        
        # Add error handler
        application.add_error_handler(error_handler)
        logger.info("Error handler added.")
        
        logger.info("Starting bot...")
        
        # Event loop handling for Python 3.14
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            logger.info("Event loop found.")
        except RuntimeError:
            logger.info("No event loop found, creating a new one...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
