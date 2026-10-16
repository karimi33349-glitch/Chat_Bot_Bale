import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== متغیرهای محیطی ==========
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")

# پیش‌فرض روی LLM7.io تنظیم شده تا از ایران بدون VPN کار کنه
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.llm7.io/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "unused")
MODEL_NAME = os.getenv("MODEL_NAME", "default")

# اگر خواستی از OpenRouter استفاده کنی، این دو تا رو ست کن:
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# OPENAI_API_KEY=sk-or-v1-...
# MODEL_NAME=meta-llama/llama-3.1-8b-instruct:free
# و در صورت نیاز HTTPS_PROXY رو هم ست کن

HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")

if HTTPS_PROXY:
    http_client = httpx.Client(proxy=HTTPS_PROXY, timeout=60.0)
    logger.info(f"Using proxy: {HTTPS_PROXY}")
else:
    http_client = httpx.Client(timeout=60.0)

client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
    http_client=http_client
)

# ========== سرور کوچک برای Render ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server listening on port {port}")
    server.serve_forever()

# ========== هندلرهای ربات ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 👋\nمن دستیار هوش مصنوعی هستم. هر سوالی داری بپرس."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"پیام دریافتی از {user_id}: {user_message}")

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer in Persian."},
                {"role": "user", "content": user_message}
            ],
            timeout=30
        )

        ai_response = response.choices[0].message.content
        logger.info(f"پاسخ AI: {ai_response}")
        await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"خطا در ارتباط با AI: {e}")
        await update.message.reply_text(
            "متأسفانه در حال حاضر قادر به پاسخگویی نیستم. لطفاً بعداً تلاش کن."
        )

# ========== اجرای اصلی ==========
def main():
    if not BALE_BOT_TOKEN:
        logger.error("❌ BALE_BOT_TOKEN تنظیم نشده است.")
        return

    # اجرای سرور سلامت در یک ترد جداگانه (برای Render)
    threading.Thread(target=run_health_server, daemon=True).start()

    application = (
        Application.builder()
        .token(BALE_BOT_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 ربات چت هوش مصنوعی بله روشن شد...")
    application.run_polling()

if __name__ == "__main__":
    main()