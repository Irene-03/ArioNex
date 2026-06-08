"""
/// <summary>
/// ماژول یکپارچه‌ساز ربات تلگرام سازمانی آریونکس (ArioNex Telegram Bot Integration)
/// </summary>
/// <remarks>
/// این ماژول ربات تلگرام متصل به موتور هوشمند RAG را به صورت ناهمگام (Async)
/// مدیریت می‌کند. این ربات قابلیت درک تاریخچه مکالمات به ازای شناسه کاربری (chat_id)،
/// فراخوانی تجمیع‌کننده معنایی و محاسباتی، و پاسخ‌دهی دقیق به همراه ارجاع به منابع را داراست.
/// </remarks>
"""

import asyncio
import logging
from typing import Dict, List
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from app.core.config import settings
from app.services.retrieval import synthesize_rag_response

logger = logging.getLogger("arionex.telegram_bot")

# ذخیره‌ساز محلی نشست‌های گفتگو به ازای هر کاربر تلگرام (In-memory Chat Session Store)
# هر نشست شامل لیستی از دیکشنری‌های پیام به صورت [{"Human": "..."}, {"AI": "..."}] است.
_chat_sessions: Dict[int, List[dict]] = {}

# مرجع اصلی آبجکت اپلیکیشن تلگرام جهت کنترل چرخه حیات در متدهای استارت و استاپ
telegram_app: Application = None

def get_chat_history(chat_id: int) -> List[dict]:
    """
    /// <summary>
    /// بازیابی تاریخچه مکالمات گذشته کاربر تلگرام با اعمال محدودیت طول تاریخچه
    /// </summary>
    /// <param name="chat_id">شناسه منحصربه‌فرد گفتگو در تلگرام</param>
    /// <returns>لیستی از پیام‌های رد و بدل شده اخیر</returns>
    """
    if chat_id not in _chat_sessions:
        _chat_sessions[chat_id] = []
    # محدود کردن تاریخچه به ۱۰ پیام اخیر جهت بهینه‌سازی مصرف توکن
    return _chat_sessions[chat_id][-10:]

def update_chat_history(chat_id: int, user_query: str, ai_response: str):
    """
    /// <summary>
    /// افزودن پرسش و پاسخ جدید به تاریخچه نشست کاربر تلگرام
    /// </summary>
    /// <param name="chat_id">شناسه منحصربه‌فرد گفتگو در تلگرام</param>
    /// <param name="user_query">سوال پرسیده شده توسط کاربر</param>
    /// <param name="ai_response">پاسخ تولید شده توسط دستیار آریونکس</param>
    /// </summary>
    """
    if chat_id not in _chat_sessions:
        _chat_sessions[chat_id] = []
    
    _chat_sessions[chat_id].append({"Human": user_query})
    _chat_sessions[chat_id].append({"AI": ai_response})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /// <summary>
    /// کنترل‌کننده دستور شروع (/start) ربات تلگرام
    /// </summary>
    """
    chat_id = update.effective_chat.id
    # پاک کردن تاریخچه گذشته در صورت استارت مجدد
    if chat_id in _chat_sessions:
        _chat_sessions[chat_id] = []
        
    welcome_text = (
        "💼 **به دستیار هوشمند سازمانی آریونکس (ArioNex) خوش آمدید!** ✨\n\n"
        "من دستیار هوش مصنوعی سازمان شما هستم و می‌توانم به صورت کاملاً امن "
        "به جستجوی اسناد، قوانین و تحلیل داده‌های مالی و حسابداری بپردازم.\n\n"
        "💬 **چگونه می‌توانم به شما کمک کنم؟**\n"
        "کافیست سوال خود را بنویسید یا اسناد مالی را جهت تحلیل مطرح نمایید."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    logger.info(f"Telegram user {chat_id} started the conversation bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /// <summary>
    /// کنترل‌کننده دستور راهنمای ربات (/help)
    /// </summary>
    """
    help_text = (
        "📚 **راهنمای استفاده از دستیار آریونکس (ArioNex Help):**\n\n"
        "🔹 **پرسش معنایی اسناد:** سوالات خود را درباره مفاد قراردادها، فایل‌های متنی یا پی‌دی‌اف‌های بارگذاری شده در سیستم بپرسید.\n"
        "🔹 **تحلیل آماری حسابداری:** با استفاده از کلیدواژه‌هایی چون *میانگین، مجموع، فاکتور، سند، تراکنش* می‌توانید داده‌های مالی دمو را تحلیل کنید.\n"
        "🔹 **قانون عدم توهم:** دستیار بر اساس مستندات واقعی پاسخ می‌دهد. در صورت نبود منابع، از ارائه حدس و توهم خودداری خواهد کرد.\n\n"
        "🔄 برای بازنشانی کامل تاریخچه چت جاری، دستور /start را ارسال کنید."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /// <summary>
    /// کنترل‌کننده اصلی پیام‌های متنی دریافتی کاربران تلگرام و اتصال به موتور RAG
    /// </summary>
    """
    if not update.message or not update.message.text:
        return
        
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()
    
    logger.info(f"Received Telegram message from user {chat_id}: '{user_text[:30]}...'")
    
    # نمایش وضعیت در حال تایپ به کاربر تلگرام
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # ۱. لود تاریخچه سشن گفتگو به ازای chat_id
        history = get_chat_history(chat_id)
        
        # ۲. فراخوانی موتور هوشمند متمرکز RAG
        result = synthesize_rag_response(
            user_input=user_text,
            chat_history=history,
            threshold=0.4,
            k=4
        )
        
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        # ۳. افزودن منابع استناد شده به صورت شکیل در پایین پاسخ تلگرامی
        if sources and "اطلاعات کافی" not in answer:
            citation_list = []
            seen_sources = set()
            for src in sources:
                src_key = f"{src['name']} ({src['page']})"
                if src_key not in seen_sources:
                    seen_sources.add(src_key)
                    citation_list.append(f"🔹 {src['name']} - {src['page']}")
            
            if citation_list:
                answer += "\n\n📚 **منابع استناد شده:**\n" + "\n".join(citation_list)
        
        # ۴. ذخیره تعامل در سشن گفتگو
        update_chat_history(chat_id, user_text, result.get("answer", ""))
        
        # ۵. ارسال پاسخ نهایی
        await update.message.reply_text(answer, parse_mode="Markdown")
        logger.info(f"Replied successfully to Telegram user {chat_id}.")
        
    except Exception as e:
        logger.error(f"Error handling Telegram message for user {chat_id}: {str(e)}")
        error_reply = "⚠️ متاسفانه در پردازش پاسخ شما خطایی در موتور هوش مصنوعی رخ داده است. لطفاً مجدداً تلاش فرمایید."
        await update.message.reply_text(error_reply)

async def init_telegram_bot() -> Application:
    """
    /// <summary>
    /// مقداردهی اولیه و ثبت کنترلرهای مختلف پیام و دستورات ربات تلگرام
    /// </summary>
    /// <returns>یک نمونه معتبر از کلاس Application متعلق به کتابخانه تلگرام</returns>
    """
    token = settings.telegram_bot_token
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty. Telegram integration will remain inactive.")
        return None
        
    try:
        app = ApplicationBuilder().token(token).build()
        
        # ثبت هندلرهای دستورات
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        
        # ثبت هندلر برای تمامی پیام‌های متنی متفرقه
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        logger.info("Telegram Bot Application initialized with handlers successfully.")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Telegram Bot application builder: {str(e)}")
        return None

async def start_telegram_bot_service():
    """
    /// <summary>
    /// راه‌اندازی و استارت فرآیند دریافت پیام‌های ربات تلگرام (Non-blocking Polling) در لایف‌اسپن FastAPI
    /// </summary>
    """
    global telegram_app
    
    # بررسی روشن بودن فیچر تاگل تلگرام در تنظیمات ادمین
    if not settings.integrations.telegram_bot:
        logger.info("Telegram Bot integration is disabled in settings. Skipping startup.")
        return
        
    telegram_app = await init_telegram_bot()
    if not telegram_app:
        logger.warning("Telegram Bot application could not be built. Skipping bot runner.")
        return
        
    try:
        logger.info("Starting Telegram Bot Polling service...")
        # اجرای ناهمگام روال‌های داخلی ربات در وب‌سرور FastAPI
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram Bot is online and actively polling.")
    except Exception as e:
        logger.error(f"Graceful start failed for Telegram Bot service: {str(e)}. Web server will continue operating normally.")

async def stop_telegram_bot_service():
    """
    /// <summary>
    /// خاموش کردن ایمن و متوقف کردن ناهمگام ربات تلگرام در زمان متوقف شدن سرور FastAPI
    /// </summary>
    """
    global telegram_app
    if telegram_app:
        try:
            logger.info("Stopping Telegram Bot polling service...")
            if telegram_app.updater:
                await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram Bot service stopped and resources freed successfully.")
        except Exception as e:
            logger.error(f"Error during Telegram Bot shutdown sequence: {str(e)}")
