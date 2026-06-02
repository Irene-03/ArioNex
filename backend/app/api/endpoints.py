"""
/// <summary>
/// اندپوینت‌های رسمی وب‌سرویس آریونکس (ArioNex REST API Endpoints)
/// </summary>
/// <remarks>
/// این ماژول تمامی اندپوینت‌های تبادل اطلاعات شامل ثبت پرسش RAG (/v1/query)،
/// آپلود اسناد به همراه مسیریابی هوشمند پردازشگرها (/v1/upload)، دریافت و ذخیره تنظیمات فیچر تاگل (/v1/config)،
/// و سرویس‌های ویژه ابزارک پاپ‌آپ وب‌سایت (/v1/widget/chat) را مدیریت می‌کند.
/// </remarks>
"""

import os
import shutil
import tempfile
import logging
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query, Response
from pydantic import BaseModel

from app.core.config import settings, Settings, ServiceToggles, IntegrationToggles, SecuritySettings
from app.services.retrieval.synthesizer import synthesize_rag_response
from app.services.workers.unstructured_processor import unstructured_processor
from app.services.workers.qna_processor import qna_processor
from app.services.workers.structured_processor import structured_processor
from app.services.safety.pii_redactor import redact_and_audit
from app.core.database import get_db_connection

logger = logging.getLogger("arionex.endpoints")

router = APIRouter(prefix="/v1", tags=["ArioNex Services v1"])

# مدلهای داده درخواست و پاسخ (Pydantic Schemas)
class QueryRequest(BaseModel):
    query: str
    session_id: str = "default_session"
    file_ids: Optional[List[int]] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    is_safe: bool = True

class ConfigUpdateRequest(BaseModel):
    services: Optional[dict] = None
    integrations: Optional[dict] = None
    security: Optional[dict] = None

# شمارنده کاذب شناسه فایل‌های آپلود شده (در حالت غیاب سکانس دیتابیس)
_file_id_counter = 100

def get_next_file_id() -> int:
    global _file_id_counter
    _file_id_counter += 1
    return _file_id_counter

@router.post("/query", response_model=QueryResponse)
async def process_rag_query(request: QueryRequest):
    """
    /// <summary>
    /// اندپوینت اصلی ثبت پرسش دستیار هوشمند با RAG متصل و ایمن
    /// </summary>
    /// <param name="request">درخواست پرسش شامل متن سوال، شناسه نشست چت و فیلتر فایل‌ها</param>
    /// <returns>پاسخ نهایی دستیار به همراه لیست منابع استناد شده</returns>
    """
    if not settings.integrations.rest_api:
        logger.warning("REST API Integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="REST API Integration channel is disabled.")
        
    try:
        # فراخوانی تجمیع‌کننده RAG
        # در فازهای بعدی، حافظه واقعی نشست چت از دیتابیس لود می‌شود. فعلا از تاریخچه پیام خالی شروع می‌کنیم.
        # تاریخچه‌های گذشته RAG را می‌توان از حافظه سشن لود کرد.
        chat_history = [] 
        
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=chat_history,
            threshold=0.4,
            k=4
        )
        
        # ذخیره در لاگ ممیزی ادمین (pg_audit_logs)
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                audit_sql = """
                INSERT INTO pg_audit_logs (user_name, user_role, query_text, response_text, status, pii_masked_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(audit_sql, ("API_User", "Developer", request.query, result["answer"], "success", 0))
                conn.commit()
            conn.close()
        except Exception as audit_err:
            logger.error(f"Audit logging failed: {str(audit_err)}")
            
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            is_safe=result["is_safe"]
        )
    except Exception as e:
        logger.error(f"Error processing API query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal RAG engine failure: {str(e)}")


@router.post("/upload")
async def upload_and_ingest_file(file: UploadFile = File(...)):
    """
    /// <summary>
    /// اندپوینت آپلود اسناد به همراه سیستم مسیریابی هوشمند خط پردازش داده (Safety Airlock Routing)
    /// </summary>
    /// <param name="file">فایل فیزیکی آپلود شده (PDF, DOCX, CSV, TXT)</param>
    /// <returns>شناسه فایل، آدرس آرشیو ابری و چانک‌های ایندکس شده</returns>
    /// <remarks>
    /// این متد فایل آپلود شده را موقتا ذخیره کرده، نوع پسوند آن را پایش کرده و بر اساس نوع ساختار
    /// به پردازشگر مربوطه (اسناد نامنظم، الگوهای پرسش و پاسخ QnA، یا جداول مالی حسابداری) هدایت می‌کند.
    /// </remarks>
    """
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())
    
    # ساخت دایرکتوری موقت و امن روی سرور جهت پارس کردن فایل
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        # ۱. ذخیره فیزیکی فایل آپلود شده موقت
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_id = get_next_file_id()
        
        # ۲. پیش‌نمایش قفل حریم شخصی (PII Redaction Preview) برای ادمین داشبورد
        pii_preview_text = ""
        pii_audit_counts = {}
        if ext in [".txt", ".csv"]:
            try:
                # خواندن چند سطر ابتدایی برای تست PII
                with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = "".join([f.readline() for _ in range(5)])
                pii_preview_text, pii_audit_counts = redact_and_audit(sample)
            except Exception:
                pii_preview_text = "Preview unavailable for binary formats."

        # ۳. سیستم هوشمند مسیریابی فایل به کارگران تخصصی (Ingestion Router)
        result_data = {}
        
        if ext == ".csv":
            # تشخیص هوشمند اینکه آیا فایل QnA است یا جدول محاسباتی پانداس
            try:
                df = pd = None
                import pandas as pd
                df = pd.read_csv(temp_path, nrows=5)
                cols_lower = [str(c).lower().strip() for c in df.columns]
                
                is_qna = any("question" in c or "answer" in c or c == "سوال" or c == "پاسخ" for c in cols_lower)
                
                if is_qna:
                    # هدایت به پردازشگر پرسش و پاسخ
                    result_data = qna_processor.process_qna_csv(temp_path, filename, file_id)
                    result_data["processor_type"] = "qna_processor"
                else:
                    # هدایت به پردازشگر داده‌های ساختاریافته مالی
                    result_data = structured_processor.process_structured_csv(temp_path, filename, file_id)
                    result_data["processor_type"] = "structured_analytics"
            except Exception as e:
                logger.error(f"Smart Ingestion Router failed to parse CSV structure: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Corrupted CSV template: {str(e)}")
        elif ext in [".pdf", ".docx", ".doc", ".txt", ".json", ".xml", ".mmd"]:
            # هدایت به پردازشگر اسناد عمومی متنی
            result_data = unstructured_processor.process_document(temp_path, filename, file_id)
            result_data["processor_type"] = "unstructured_document"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")
            
        # ۴. بازگرداندن نتایج نهایی به پنل ری‌اکت
        return {
            "file_id": file_id,
            "filename": filename,
            "status": "success",
            "processor": result_data.get("processor_type"),
            "chunks_indexed": result_data.get("chunks_count", 0),
            "archive_url": result_data.get("storage_url", "local"),
            "pii_audit_counts": pii_audit_counts,
            "pii_preview": pii_preview_text
        }
        
    except Exception as e:
        logger.error(f"File upload and ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(e)}")
    finally:
        # حذف فایل‌های موقت جهت خالی کردن هارد سرور
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


@router.get("/config")
async def get_active_configuration():
    """
    /// <summary>
    /// اندپوینت دریافت کانفیگ زنده و وضعیت روشن/خاموش بودن تمامی سرویس‌های تاگل
    /// </summary>
    """
    return {
        "services": settings.services.__dict__,
        "integrations": settings.integrations.__dict__,
        "security": settings.security.__dict__
    }


@router.post("/config")
async def update_active_configuration(update: ConfigUpdateRequest):
    """
    /// <summary>
    /// اندپوینت ادمین پنل جهت تغییر زنده و داینامیک تنظیمات سرویس‌ها و درگاه‌های خروجی
    /// </summary>
    """
    try:
        # تغییر در تنظیمات لود شده سراسری برنامه
        if update.services:
            for k, v in update.services.items():
                if hasattr(settings.services, k):
                    setattr(settings.services, k, bool(v))
        if update.integrations:
            for k, v in update.integrations.items():
                if hasattr(settings.integrations, k):
                    setattr(settings.integrations, k, bool(v))
        if update.security:
            for k, v in update.security.items():
                if hasattr(settings.security, k):
                    setattr(settings.security, k, bool(v))
                    
        logger.info("Administrative Feature Toggles updated successfully at runtime.")
        return {
            "status": "success",
            "message": "Configuration updated at runtime.",
            "current_config": {
                "services": settings.services.__dict__,
                "integrations": settings.integrations.__dict__,
                "security": settings.security.__dict__
            }
        }
    except Exception as e:
        logger.error(f"Failed to update runtime configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ذخیره‌ساز محلی نشست‌های گفتگو برای ابزارک چت وب‌سایت (In-memory Chat Session Store for Web Widget)
_widget_sessions: dict[str, list] = {}

@router.get("/widget.js")
async def get_web_widget_script():
    """
    /// <summary>
    /// اندپوینت دریافت فایل جاوااسکریپت ابزارک چت پاپ‌آپ وب‌سایت
    /// </summary>
    /// <returns>کدهای جاوااسکریپت خودمحور با استایل‌دهی لوکس و بومی</returns>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is disabled in settings.")
        return Response(
            content="console.warn('ArioNex Website Chat Widget is disabled by the administrator.');",
            media_type="application/javascript"
        )
        
    # کدهای جاوااسکریپت و CSS به صورت یکپارچه و بهینه شده
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
        .arionex-widget-header-close:hover {
            color: #c4894a;
        }
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
        .arionex-widget-input:focus {
            border-color: #c4894a;
        }
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
        .arionex-widget-send:hover {
            background-color: #c4894a;
        }
        .arionex-widget-watermark {
            text-align: center;
            font-size: 10px;
            color: rgba(15, 26, 46, 0.4);
            padding: 4px;
            background: #ffffff;
        }
    `;
    document.head.appendChild(style);

    // ساخت حباب شناور در گوشه صفحه
    const bubble = document.createElement('div');
    bubble.className = 'arionex-widget-bubble';
    bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>`;
    document.body.appendChild(bubble);

    // ساخت پنجره چت
    const container = document.createElement('div');
    container.className = 'arionex-widget-container';
    container.innerHTML = `
        <div class="arionex-widget-header">
            <div class="arionex-widget-header-title">
                <span>🛡️ دستیار هوشمند آریونکس</span>
            </div>
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
        <div class="arionex-widget-watermark">
            پشتیبانی شده توسط هوش سازمانی ArioNex ©
        </div>
    `;
    document.body.appendChild(container);

    const messagesContainer = container.querySelector('.arionex-widget-messages');
    const inputField = container.querySelector('.arionex-widget-input');
    const sendButton = container.querySelector('.arionex-widget-send');
    const closeButton = container.querySelector('.arionex-widget-header-close');

    // مدیریت باز و بسته شدن پنجره چت
    bubble.addEventListener('click', () => {
        const isVisible = container.style.display === 'flex';
        container.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            inputField.focus();
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    });

    closeButton.addEventListener('click', () => {
        container.style.display = 'none';
    });

    // متد ارسال پیام کاربر به بک‌اند
    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        inputField.value = '';

        // نمایش پیام کاربر در چت باکس
        const userMsg = document.createElement('div');
        userMsg.className = 'arionex-widget-message arionex-widget-message-user';
        userMsg.textContent = text;
        messagesContainer.appendChild(userMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // نمایش لودر انیمیشنی لود در زمان فراخوانی RAG
        const loader = document.createElement('div');
        loader.className = 'arionex-widget-loader';
        loader.innerHTML = '<div class="arionex-widget-dot"></div><div class="arionex-widget-dot"></div><div class="arionex-widget-dot"></div>';
        messagesContainer.appendChild(loader);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            // فراخوانی اندپوینت ارتباطی ابزارک وب با آدرس مطلق
            const response = await fetch('http://localhost:8000/v1/widget/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: text,
                    session_id: sessionId
                })
            });

            const data = await response.json();
            messagesContainer.removeChild(loader);

            // نمایش پاسخ هوش مصنوعی
            const botMsg = document.createElement('div');
            botMsg.className = 'arionex-widget-message arionex-widget-message-bot';
            
            let replyText = data.answer || "⚠️ مشکلی در دریافت پاسخ پیش آمده است.";
            
            // قالب‌بندی و نمایش منابع به صورت تفکیک شده
            if (data.sources && data.sources.length > 0 && !replyText.includes("اطلاعات کافی")) {
                const uniqueSources = [];
                const seen = new Set();
                data.sources.forEach(src => {
                    const key = src.name + " (" + src.page + ")";
                    if (!seen.has(key)) {
                        seen.add(key);
                        uniqueSources.push(src.name + " - " + src.page);
                    }
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
            console.error("ArioNex Widget API Error:", error);
            messagesContainer.removeChild(loader);
            
            const errMsg = document.createElement('div');
            errMsg.className = 'arionex-widget-message arionex-widget-message-bot';
            errMsg.textContent = "⚠️ خطا در برقراری ارتباط با سرور هوشمند آریونکس. لطفاً مجدداً امتحان کنید.";
            messagesContainer.appendChild(errMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
})();"""
    return Response(content=js_code, media_type="application/javascript")


@router.post("/widget/chat", response_model=QueryResponse)
async def process_widget_query(request: QueryRequest):
    """
    /// <summary>
    /// اندپوینت اختصاصی تبادل پیام و دریافت پاسخ‌های RAG برای ابزارک پاپ‌آپ وب‌سایت
    /// </summary>
    /// <param name="request">درخواست شامل متن پرسش و شناسه نشست کاربر</param>
    /// <returns>پاسخ نهایی دستیار به همراه آرایه منابع استنادی</returns>
    """
    if not settings.integrations.popup_widget:
        logger.warning("Pop-up Website Widget integration is currently disabled in settings.")
        raise HTTPException(status_code=403, detail="Website Pop-up Widget channel is disabled.")
        
    try:
        # ۱. بازیابی تاریخچه مکالمات ابزارک بر اساس شناسه نشست
        session_id = request.session_id
        if session_id not in _widget_sessions:
            _widget_sessions[session_id] = []
            
        history = _widget_sessions[session_id][-10:] # حداکثر ۱۰ پیام اخیر
        
        # ۲. فراخوانی موتور RAG متمرکز
        result = synthesize_rag_response(
            user_input=request.query,
            chat_history=history,
            threshold=0.4,
            k=4
        )
        
        # ۳. ذخیره تعامل در سشن گفتگو جهت حفظ پیوستگی چت
        _widget_sessions[session_id].append({"Human": request.query})
        _widget_sessions[session_id].append({"AI": result["answer"]})
        
        # ۴. ثبت در سیستم ممیزی ادمین (pg_audit_logs)
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                audit_sql = """
                INSERT INTO pg_audit_logs (user_name, user_role, query_text, response_text, status, pii_masked_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(audit_sql, ("Widget_User", "Viewer", request.query, result["answer"], "success", 0))
                conn.commit()
            conn.close()
        except Exception as audit_err:
            logger.error(f"Widget audit logging failed: {str(audit_err)}")
            
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            is_safe=result["is_safe"]
        )
    except Exception as e:
        logger.error(f"Error processing widget chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Widget RAG failure: {str(e)}")

