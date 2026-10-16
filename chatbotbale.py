import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from dotenv import load_dotenv
import httpx # اضافه کردن این کتابخانه

# ========== بارگذاری متغیرهای محیطی ==========
load_dotenv()

# ========== تنظیمات لاگ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== توکن‌ها ==========
TOKEN = os.environ.get("BALE_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ========== تنظیمات پروکسی ==========
# این متغیرها را می‌توانید از محیط سیستم یا فایل .env بخوانید
# مثال: HTTPS_PROXY="http://127.0.0.1:10809"
PROXY_URL = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")

# --- راه‌اندازی کلاینت LLM7.io (بدون نیاز به پروکسی) ---
import httpx

client = OpenAI(
    base_url="https://api.llm7.io/v1", # آدرس سرویس LLM7.io
    api_key="unused", # نیازی به کلید معتبر نیست
    http_client=httpx.Client(timeout=60.0) # بدون پروکسی
)

# --- انتخاب مدل ---
MODEL_NAME = "fast" # یا "fast" برای پاسخ‌های سریع‌تر

# ========== دستور شروع ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام خوش‌آمدگویی"""
    await update.message.reply_text(
        "🤖 سلام! من دستیار هوش مصنوعی شما هستم.\n"
        "هر سوالی دارید بپرسید، در خدمتم!"
    )

# ========== هندلر پیام‌های متنی ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پیام کاربر، ارسال به هوش مصنوعی و بازگرداندن پاسخ"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    logger.info(f"پیام دریافتی از {user_id}: {user_message}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ],
            timeout=30 # Timeout خود را می‌توانید اینجا تنظیم کنید
        )

        ai_response = response.choices[0].message.content
        logger.info(f"پاسخ هوش مصنوعی: {ai_response}")

        await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"خطا در ارتباط با OpenRouter: {e}")
        await update.message.reply_text(
            "متأسفانه در حال حاضر قادر به پاسخگویی نیستم. لطفاً بعداً تلاش کنید."
        )

# ========== تابع اصلی ==========
def main():
    """راه‌اندازی و اجرای ربات"""
    if not TOKEN:
        logger.error("❌ توکن ربات بله تنظیم نشده است.")
        return
    if not OPENROUTER_API_KEY:
        logger.error("❌ کلید API اوپن‌روتر تنظیم نشده است.")
        return

    application = Application.builder() \
        .token(TOKEN) \
        .base_url('https://tapi.bale.ai/bot') \
        .connect_timeout(60) \
        .read_timeout(60) \
        .write_timeout(60) \
        .build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 ربات چت هوش مصنوعی بله روشن شد...")
    application.run_polling()

if __name__ == '__main__':
    main()