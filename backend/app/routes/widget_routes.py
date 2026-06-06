"""
/// <summary>
/// روتر ابزارک چت پاپ‌آپ وب‌سایت آریونکس (ArioNex Web Widget Chat Router)
/// </summary>
/// <remarks>
/// این ماژول دو اندپوینت ابزارک وب‌سایت را تعریف می‌کند:
///   ۱. GET /v1/widget.js   — فایل JavaScript پاپ‌آپ چت
///   ۲. POST /v1/widget/chat — اندپوینت پردازش پیام چت ابزارک
///
/// منطق session و RAG در widget_logic.py قرار دارد.
/// کد JavaScript به صورت inline داخل این روتر نگهداری می‌شود — چون مستقیماً به endpoint مربوط است.
/// </remarks>
"""

import logging
from typing import Optional
from fastapi import APIRouter, Response
from app.core.config import settings
from app.core.database import get_db_connection
from app.schemas.query_schemas import QueryRequest, QueryResponse
from app.logics.widget_logic import execute_widget_logic

logger = logging.getLogger("arionex.widget_routes")
router = APIRouter(prefix="/v1", tags=["Widget — Website Chat Popup"])


@router.get(
    "/widget.js",
    summary="دریافت فایل JavaScript ابزارک چت پاپ‌آپ",
    description="اسکریپت JavaScript خودمحور (self-contained) ابزارک چت وب‌سایت را برمی‌گرداند.",
)
async def get_web_widget_script(website: Optional[str] = None):
    """
    /// <summary>
    /// اندپوینت دریافت فایل جاوااسکریپت ابزارک چت پاپ‌آپ وب‌سایت
    /// </summary>
    /// <param name="website">آدرس وب‌سایت درخواست‌دهنده جهت شخصی‌سازی تم و پیام</param>
    /// <returns>کدهای جاوااسکریپت خودمحور با استایل‌دهی لوکس و بومی</returns>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is disabled in settings.")
        return Response(
            content="console.warn('ArioNex Website Chat Widget is disabled by the administrator.');",
            media_type="application/javascript",
        )

    # مقادیر پیش‌فرض تم و پیام خوش‌آمدگویی
    welcome_message = "سلام! من دستیار هوشمند آریونکس (ArioNex) هستم. چطور می‌توانم به شما کمک کنم؟ 💼✨"
    theme_color = "#1a2744"
    accent_color = "#c4894a"

    if website:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT welcome_message, theme_color, accent_color FROM website_widgets WHERE %s LIKE '%' || url || '%' OR url LIKE '%' || %s || '%' LIMIT 1",
                    (website, website)
                )
                row = cur.fetchone()
                if row:
                    welcome_message = row[0] or welcome_message
                    theme_color = row[1] or theme_color
                    accent_color = row[2] or accent_color
                    logger.info(f"Loaded customized widget config for website='{website}': theme_color={theme_color}")
        except Exception as e:
            logger.error(f"Error querying website widget database: {str(e)}")
        finally:
            if conn:
                conn.close()

    js_code = """(function() {
    // ایجاد شناسه مکالمه منحصربه‌فرد برای کاربر و ذخیره در حافظه محلی مرورگر
    let sessionId = localStorage.getItem('arionex_widget_session_id');
    if (!sessionId) {
        sessionId = 'widget_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('arionex_widget_session_id', sessionId);
    }

    // تزریق مستقیم کدهای استایل CSS به سند جهت استایل‌دهی لوکس و هم‌ساز
    const style = document.createElement('style');
    style.innerHTML = `
        .arionex-widget-bubble {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1a2744 0%, #0f1a2e 100%);
            box-shadow: 0 4px 15px rgba(15, 26, 46, 0.4);
            cursor: pointer;
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 2px solid #c4894a;
        }
        .arionex-widget-bubble:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(196, 137, 74, 0.6);
        }
        .arionex-widget-bubble svg {
            width: 28px;
            height: 28px;
            fill: #c4894a;
        }
        .arionex-widget-container {
            position: fixed;
            bottom: 95px;
            right: 25px;
            width: 380px;
            height: 520px;
            border-radius: 16px;
            background-color: #f8f6f3;
            box-shadow: 0 10px 30px rgba(15, 26, 46, 0.25);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 999999;
            font-family: system-ui, -apple-system, sans-serif;
            border: 1px solid rgba(196, 137, 74, 0.3);
            direction: rtl;
            transition: all 0.3s ease;
        }
        .arionex-widget-header {
            background-color: #0f1a2e;
            color: #f8f6f3;
            padding: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid #c4894a;
        }
        .arionex-widget-header-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: bold;
            font-size: 16px;
            color: #c4894a;
        }
        .arionex-widget-header-close {
            cursor: pointer;
            font-size: 20px;
            color: #f8f6f3;
            transition: color 0.2s;
        }
        .arionex-widget-header-close:hover { color: #c4894a; }
        .arionex-widget-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .arionex-widget-message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.6;
            word-wrap: break-word;
        }
        .arionex-widget-message-user {
            align-self: flex-start;
            background-color: #1a2744;
            color: #f8f6f3;
            border-bottom-left-radius: 2px;
        }
        .arionex-widget-message-bot {
            align-self: flex-end;
            background-color: #ffffff;
            color: #0f1a2e;
            border: 1px solid rgba(196, 137, 74, 0.15);
            border-bottom-right-radius: 2px;
        }
        .arionex-widget-message-sources {
            margin-top: 8px;
            font-size: 11px;
            border-top: 1px dashed rgba(196, 137, 74, 0.3);
            padding-top: 6px;
            color: #c4894a;
        }
        .arionex-widget-loader {
            display: flex;
            align-self: flex-end;
            background: #ffffff;
            border: 1px solid rgba(196, 137, 74, 0.15);
            padding: 12px;
            border-radius: 12px;
            border-bottom-right-radius: 2px;
            gap: 4px;
        }
        .arionex-widget-dot {
            width: 8px;
            height: 8px;
            background: #c4894a;
            border-radius: 50%;
            animation: arionex-dot-blink 1.4s infinite both;
        }
        .arionex-widget-dot:nth-child(2) { animation-delay: 0.2s; }
        .arionex-widget-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes arionex-dot-blink {
            0% { opacity: .2; }
            20% { opacity: 1; }
            100% { opacity: .2; }
        }
        .arionex-widget-footer {
            padding: 12px;
            background: #ffffff;
            border-top: 1px solid rgba(196, 137, 74, 0.2);
            display: flex;
            gap: 8px;
        }
        .arionex-widget-input {
            flex: 1;
            border: 1px solid rgba(15, 26, 46, 0.15);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
            font-family: inherit;
        }
        .arionex-widget-input:focus { border-color: #c4894a; }
        .arionex-widget-send {
            background-color: #1a2744;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
            font-family: inherit;
        }
        .arionex-widget-send:hover { background-color: #c4894a; }
        .arionex-widget-watermark {
            text-align: center;
            font-size: 10px;
            color: rgba(15, 26, 46, 0.4);
            padding: 4px;
            background: #ffffff;
        }
    `;
    document.head.appendChild(style);

    const bubble = document.createElement('div');
    bubble.className = 'arionex-widget-bubble';
    bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>`;
    document.body.appendChild(bubble);

    const container = document.createElement('div');
    container.className = 'arionex-widget-container';
    container.innerHTML = `
        <div class="arionex-widget-header">
            <div class="arionex-widget-header-title"><span>🛡️ دستیار هوشمند آریونکس</span></div>
            <div class="arionex-widget-header-close">✕</div>
        </div>
        <div class="arionex-widget-messages">
            <div class="arionex-widget-message arionex-widget-message-bot">
                سلام! من دستیار هوشمند آریونکس (ArioNex) هستم. چطور می‌توانم به شما کمک کنم؟ 💼✨
            </div>
        </div>
        <div class="arionex-widget-footer">
            <input type="text" class="arionex-widget-input" placeholder="سوال خود را اینجا بنویسید..." />
            <button class="arionex-widget-send">ارسال</button>
        </div>
        <div class="arionex-widget-watermark">پشتیبانی شده توسط هوش سازمانی ArioNex ©</div>
    `;
    document.body.appendChild(container);

    const messagesContainer = container.querySelector('.arionex-widget-messages');
    const inputField = container.querySelector('.arionex-widget-input');
    const sendButton = container.querySelector('.arionex-widget-send');
    const closeButton = container.querySelector('.arionex-widget-header-close');

    bubble.addEventListener('click', () => {
        const isVisible = container.style.display === 'flex';
        container.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) { inputField.focus(); messagesContainer.scrollTop = messagesContainer.scrollHeight; }
    });

    closeButton.addEventListener('click', () => { container.style.display = 'none'; });

    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;
        inputField.value = '';

        const userMsg = document.createElement('div');
        userMsg.className = 'arionex-widget-message arionex-widget-message-user';
        userMsg.textContent = text;
        messagesContainer.appendChild(userMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        const loader = document.createElement('div');
        loader.className = 'arionex-widget-loader';
        loader.innerHTML = '<div class="arionex-widget-dot"></div><div class="arionex-widget-dot"></div><div class="arionex-widget-dot"></div>';
        messagesContainer.appendChild(loader);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch('http://localhost:8000/v1/widget/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, session_id: sessionId })
            });

            const data = await response.json();
            messagesContainer.removeChild(loader);

            const botMsg = document.createElement('div');
            botMsg.className = 'arionex-widget-message arionex-widget-message-bot';

            let replyText = data.answer || '⚠️ مشکلی در دریافت پاسخ پیش آمده است.';

            if (data.sources && data.sources.length > 0 && !replyText.includes('اطلاعات کافی')) {
                const uniqueSources = [];
                const seen = new Set();
                data.sources.forEach(src => {
                    const key = src.name + ' (' + src.page + ')';
                    if (!seen.has(key)) { seen.add(key); uniqueSources.push(src.name + ' - ' + src.page); }
                });
                if (uniqueSources.length > 0) {
                    replyText += '<div class="arionex-widget-message-sources">📚 <b>منابع:</b><br>' +
                                 uniqueSources.map(s => '• ' + s).join('<br>') + '</div>';
                }
            }

            botMsg.innerHTML = replyText.replace(/\\n/g, '<br>');
            messagesContainer.appendChild(botMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

        } catch (error) {
            console.error('ArioNex Widget API Error:', error);
            messagesContainer.removeChild(loader);
            const errMsg = document.createElement('div');
            errMsg.className = 'arionex-widget-message arionex-widget-message-bot';
            errMsg.textContent = '⚠️ خطا در برقراری ارتباط با سرور هوشمند آریونکس. لطفاً مجدداً امتحان کنید.';
            messagesContainer.appendChild(errMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });
})();"""

    # اعمال پویای تنظیمات ابزارک
    custom_js = js_code.replace("#1a2744", theme_color)
    custom_js = custom_js.replace("#c4894a", accent_color)
    custom_js = custom_js.replace(
        "سلام! من دستیار هوشمند آریونکس (ArioNex) هستم. چطور می‌توانم به شما کمک کنم؟ 💼✨",
        welcome_message
    )

    return Response(content=custom_js, media_type="application/javascript")


@router.post(
    "/widget/chat",
    response_model=QueryResponse,
    summary="پردازش پیام ابزارک چت وب‌سایت",
    description="پرسش ارسال شده از ابزارک پاپ‌آپ وب‌سایت را دریافت کرده و با حفظ تاریخچه نشست پاسخ می‌دهد.",
)
async def process_widget_query(request: QueryRequest):
    """
    /// <summary>
    /// اندپوینت اختصاصی تبادل پیام ابزارک پاپ‌آپ وب‌سایت
    /// </summary>
    /// <param name="request">درخواست شامل متن پرسش و شناسه نشست کاربر</param>
    /// <returns>پاسخ نهایی دستیار به همراه آرایه منابع استنادی</returns>
    """
    return await execute_widget_logic(request)
